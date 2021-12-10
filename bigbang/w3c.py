import email
from urllib.parse import urljoin, urlparse
import datetime
import yaml
import email.header
import email.parser
import gzip
import logging
import mailbox
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import requests
from mailbox import mboxMessage
from email.mime.text import MIMEText
import pandas as pd

import dateutil
from bs4 import BeautifulSoup

import bigbang.archive as archive
import bigbang.mailman as mailman

from config.config import CONFIG

from bigbang.bigbang_io import (
    ListservMessageIO,
    ListservListIO,
    ListservArchiveIO,
)
from bigbang.utils import (
    get_paths_to_files_in_directory,
    get_paths_to_dirs_in_directory,
)

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
logging.basicConfig(
    filename=directory_project + "/w3c.scraping.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


class W3CMessageParserWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class W3CListWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class W3CArchiveWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class W3CMessageParser(email.parser.Parser):
    """
    This class handles the creation of an mailbox.mboxMessage object
    (using the from_*() methods) and its storage in various other file formats
    (using the to_*() methods) that can be saved on the local memory.

    Parameters
    ----------
    website : Set 'True' if messages are going to be scraped from websites,
        otherwise 'False' if read from local memory.
    url_login : URL to the 'Log In' page.
    url_pref : URL to the 'Preferences'/settings page.
    login : Login credentials (username and password) that were used to set
        up AuthSession. You can create your own for the 3GPP archive.
    session : requests.Session() object for the Email archive website.

    Methods
    -------
    from_url()
    _get_header_from_html()
    _get_body_from_html()
    get_datetime()

    Example
    -------
    To create a Email message parser object, use the following syntax:
    >>> msg_parser = W3CMessageParser(
    >>>     website=True,
    >>>     login={"username": <your_username>, "password": <your_password>},
    >>> )
    """

    empty_header = {}

    def __init__(
        self,
        website=False,
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[requests.Session] = None,
    ):
        if website:
            if session is None:
                session = get_auth_session(url_login, **login)
                session = set_website_preference_for_header(url_pref, session)
            self.session = session

    def create_email_message(
        self,
        archived_at: str,
        body: str,
        **header,
    ) -> mboxMessage:
        """
        Parameters
        ----------
        archived_at : URL to the Email message.
        body : String that contains the body of the message.
        header : Dictionary that contains all available header fields of the
            message.
        """
        # crea EmailMessage
        msg = email.message.EmailMessage()
        if body is not None:
            try:
                msg.set_content(body)  # don't use charset="utf-16"
            except Exception:
                # UnicodeEncodeError: 'utf-16' codec can't encode character
                # '\ud83d' in position 8638: surrogates not allowed
                pass
        for key, value in header.items():
            if "content-type" == key:
                msg.set_param("Content-Type", value)
            elif "mime-version" == key:
                msg.set_param("MIME-Version", value)
            elif "content-transfer-encoding" == key:
                msg.set_param("Content-Transfer-Encoding", value)
            else:
                try:
                    # TODO: find out why it sometimes raises
                    # email/_header_value_parser.py
                    # IndexError: list index out of range.
                    # Also look into UTF-8 encoding.
                    msg[key] = value
                except Exception:
                    pass
        if (
            (msg["Message-ID"] is None)
            and (msg["Date"] is not None)
            and (msg["From"] is not None)
        ):
            msg["Message-ID"] = archived_at.split("/")[-1]
        # convert to EmailMessage to mboxMessage
        mbox_msg = mboxMessage(msg)
        mbox_msg.add_header("Archived-At", "<" + archived_at + ">")
        return mbox_msg

    def from_url(
        self,
        list_name: str,
        url: str,
        fields: str = "total",
    ) -> mboxMessage:
        """
        Parameters
        ----------
        list_name : The name of the W3C Email list.
        url : URL of this Email
        fields : Indicates whether to return 'header', 'body' or 'total'/both or
            the Email. The latter is the default.
        """
        soup = get_website_content(url, session=self.session)
        if soup == "RequestException":
            body = "RequestException"
            header = self.empty_header
        else:
            if fields in ["header", "total"]:
                header = self._get_header_from_html(soup)
            else:
                header = self.empty_header
            if fields in ["body", "total"]:
                body = self._get_body_from_html(list_name, url, soup)
            else:
                body = None
        return self.create_email_message(url, body, **header)

    def _get_header_from_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Lexer for the message header.

        Parameters
        ----------
        soup : HTML code from which the Email header can be obtained.
        """
        try:
            for string in ["Subject", "SUBJECT"]:
                try:
                    _text = soup.find(
                        "b",
                        text=re.compile(r"^\b%s\b" % string),
                    )  # Sometimes this returns None!
                    text = _text.parent.parent.parent.parent  # .text
                    break
                except Exception:
                    continue
            # collect important info from W3C header
            header = {}
            for line in text.find_all("tr"):
                key = str(line.find_all(re.compile("^b"))[0])
                key = re.search(r"<b>(.*?)<\/b>", key).group(1).lower()
                key = re.sub(r":", "", key).strip()
                if "subject" in key:
                    value = repr(
                        str(line.find_all(re.compile("^a"))[0].text).strip()
                    )
                else:
                    value = repr(str(line.find_all(re.compile("^p"))[1]))
                    value = re.search(r"<p>(.*)<\/p>", value).group(1)
                    value = value.split(" <")[0]
                value = re.sub(r"&gt;", ">", value).strip()
                value = re.sub(r"&lt;", "<", value).strip()
                # remove Carriage return
                value = re.sub(r"\\r", "", value).strip()
                # remove Linefeed
                value = re.sub(r"\\n", "", value).strip()
                if "parts/attachments" in key:
                    break
                elif "comments" in key:
                    key = "comments-to"
                    value = re.sub(r"To:", "", value).strip()
                header[key] = value
        except Exception:
            header = self.empty_header
        return header

    def _get_body_from_html(
        self, list_name: str, url: str, soup: BeautifulSoup
    ) -> Union[str, None]:
        """
        Lexer for the message body/payload.
        This methods look first whether the body is available in text/plain,
        before it looks for the text/html option. If neither is available it
        returns None.

        Therefore this method does not try to return the richest information
        content, but simply the ascii format.

        Parameters
        ----------
        list_name : The name of the LISTSERV Email list.
        url : URL to the Email.
        soup : HTML code from which the Email body can be obtained.
        """
        # TODO re-write using email.parser.Parser
        url_root = ("/").join(url.split("/")[:-2])
        a_tags = soup.select(f'a[href*="A3="][href*="{list_name}"]')
        href_plain_text = [
            tag.get("href") for tag in a_tags if "Fplain" in tag.get("href")
        ]
        href_html_text = [
            tag.get("href") for tag in a_tags if "Fhtml" in tag.get("href")
        ]
        try:
            if href_plain_text:
                body_soup = get_website_content(
                    urljoin(url_root, href_plain_text[0])
                )
                if body_soup == "RequestException":
                    return body_soup
                else:
                    return body_soup.find("pre").text
            elif href_html_text:
                body_soup = get_website_content(
                    urljoin(url_root, href_html_text[0])
                )
                if body_soup == "RequestException":
                    return body_soup
                else:
                    return body_soup.get_text(strip=True)
        except Exception:
            logger.info(
                f"The message body of {url} which is part of the "
                f"list {list_name} could not be loaded."
            )
            return None

    @staticmethod
    def get_datetime(line: str) -> str:
        """
        Parameters
        ----------
        line : String that contains date and time.
        """
        line = (" ").join(line.split(" ")[:-1]).lstrip()
        # convert format to local version of date and time
        date_time_obj = datetime.datetime.strptime(
            line, "%a, %d %b %Y %H:%M:%S"
        )
        return date_time_obj.strftime("%c")

    @staticmethod
    def create_message_id(date: str, from_address: str) -> str:
        """
        Parameters
        ----------
        date : Date and time of Email.
        from_address : The sender address of the Email.
        """
        message_id = (".").join([date, from_address])
        # remove special characters
        message_id = re.sub(r"[^a-zA-Z0-9]+", "", message_id)
        return message_id

    @staticmethod
    def to_dict(msg: mboxMessage) -> Dict[str, List[str]]:
        """Convert mboxMessage to a Dictionary"""
        return ListservMessageIO.to_dict(msg)

    @staticmethod
    def to_pandas_dataframe(msg: mboxMessage) -> pd.DataFrame:
        """Convert mboxMessage to a pandas.DataFrame"""
        return ListservMessageIO.to_pandas_dataframe(msg)

    @staticmethod
    def to_mbox(msg: mboxMessage, filepath: str):
        """
        Parameters
        ----------
        msg : The Email.
        filepath : Path to file in which the Email will be stored.
        """
        return ListservMessageIO.to_mbox(msg, filepath)


class W3cMailingListArchivesParser(email.parser.Parser):
    """
    A subclass of email.parser.Parser that parses the HTML of single-message
    archive pages generated by W3C's mail archives system, based on Hypermail.
    """

    parse = None
    # doesn't implement the file version

    # TODO: ignore spam (has separate error message in w3c archives)
    def parsestr(self, text, headersonly=False):
        """
        Takes the full HTML of a single message page; returns an email Message
        as an mboxMessage, with appropriate From separator line.

        headersonly is not supported. Not all headers are being parsed yet.
        """
        soup = BeautifulSoup(text, "html.parser")
        body = self._text_for_selector(soup, "#body")
        msg = MIMEText(body, "plain", "utf-8")

        from_text = self._parse_dfn_header(
            self._text_for_selector(soup, "#from")
        )
        from_name = from_text.split("<")[0].strip()
        from_address = self._text_for_selector(soup, "#from a")

        from_addr = email.utils.formataddr(
            (from_name, email.header.Header(from_address).encode())
        )
        msg["From"] = from_addr

        subject = self._text_for_selector(soup, "h1")
        msg["Subject"] = subject

        message_id = self._parse_dfn_header(
            self._text_for_selector(soup, "#message-id")
        )
        msg["Message-ID"] = message_id.strip()

        message_date = self._parse_dfn_header(
            self._text_for_selector(soup, "#date")
        )
        msg["Date"] = message_date.strip()

        message_to = self._parse_dfn_header(
            self._text_for_selector(soup, "#to")
        )
        if message_to:
            msg["To"] = message_to.strip()

        message_cc = self._parse_dfn_header(
            self._text_for_selector(soup, "#cc")
        )
        if message_cc:
            msg["Cc"] = message_cc.strip()

        in_reply_to_pattern = re.compile('<!-- inreplyto="(.+?)"')
        match = in_reply_to_pattern.search(str(text))
        if match:
            msg["In-Reply-To"] = "<" + match.groups()[0] + ">"

        mbox_message = mailbox.mboxMessage(msg)
        mbox_message.set_from(
            email.header.Header(from_address).encode(),
            email.utils.parsedate(message_date),
        )

        return mbox_message

    def _parse_dfn_header(self, header_text):
        header_texts = str(header_text).split(":", 1)
        if len(header_texts) == 2:
            return header_texts[1]
        else:
            logging.debug("Split failed on %s", header_text)
            return ""

    def _text_for_selector(self, soup, selector):
        results = soup.select(selector)
        if results:
            result = results[0].get_text(strip=True)
        else:
            result = ""
            logging.debug("No matching text for selector %s", selector)

        return str(result)


def collect_from_url(url, base_arch_dir="archives", notes=None):
    """
    Collects W3C mailing list archives from a particular mailing list URL.

    Logs an error and returns False if no messages can be collected.
    """
    list_name = mailman.get_list_name(url)
    logging.info("Getting W3C list archive for %s", list_name)

    try:
        response = urllib.request.urlopen(url)
        response_url = response.geturl()
        html = response.read()
        soup = BeautifulSoup(html, "html.parser")
    except urllib.error.HTTPError:
        logging.exception("Error in loading W3C list archive page for %s", url)
        return False

    try:
        time_period_indices = list()
        rows = soup.select("tbody tr")
        for row in rows:
            link = row.select("td:nth-of-type(1) a")[0].get("href")
            logging.info("Found time period archive page: %s", link)
            time_period_indices.append(link)
    except Exception:
        logging.exception("Error in parsing list archives for %s", url)
        return False

    # directory for downloaded files
    arc_dir = archive.archive_directory(base_arch_dir, list_name)
    mailman.populate_provenance(
        directory=arc_dir,
        list_name=list_name,
        list_url=url,
        notes=notes,
    )

    for link in time_period_indices:

        try:
            link_url = urllib.parse.urljoin(response_url, link)
            response = urllib.request.urlopen(link_url)
            html = response.read()
            soup = BeautifulSoup(html, "html.parser")
        except urllib.error.HTTPError:
            logging.exception("Error in loading: %s", link_url)
            return False

        end_date_string = (
            soup.select("#end")[0].parent.parent.select("em")[0].get_text()
        )
        end_date = dateutil.parser.parse(end_date_string)
        year_month_mbox = end_date.strftime("%Y-%m") + ".mbox"
        mbox_path = os.path.join(arc_dir, year_month_mbox)

        # looks like we've already downloaded this timeperiod
        if os.path.isfile(mbox_path):
            logging.info("Looks like %s already exists, moving on.", mbox_path)
            continue
        logging.info("Downloading messages to archive to %s.", mbox_path)

        message_links = list()
        messages = list()

        anchors = soup.select("div.messages-list a")
        for anchor in anchors:
            if anchor.get("href"):
                message_url = urllib.parse.urljoin(
                    link_url, anchor.get("href")
                )
                message_links.append(message_url)

        for message_link in message_links:
            response = urllib.request.urlopen(message_link)
            html = response.read()

            message = W3cMailingListArchivesParser().parsestr(html)
            message.add_header("Archived-At", "<" + message_link + ">")
            messages.append(message)
            time.sleep(1)  # wait between loading messages, for politeness

        mbox = mailbox.mbox(mbox_path)
        mbox.lock()

        try:
            for message in messages:
                mbox.add(message)
            mbox.flush()
        finally:
            mbox.unlock()

        logging.info("Saved %s", year_month_mbox)

    # assumes all archives were downloaded if no exceptions have been thrown
    provenance = mailman.access_provenance(arc_dir)
    provenance["complete"] = True
    mailman.update_provenance(arc_dir, provenance)


def set_website_preference_for_header(
    url_pref: str,
    session: requests.Session,
) -> requests.Session:
    """
    Set the 'Email Headers' of the 'Archive Preferences' for the auth session
    to 'Show All Headers'. Otherwise only a restricted list of header fields is
    shown.
    """
    url_archpref = url_pref + "&TAB=2"
    payload = {
        "Email Headers": "b",
    }
    session.post(url_archpref, data=payload)
    return session


def get_auth_session(
    url_login: str, username: str, password: str
) -> requests.Session:
    """
    Create AuthSession.

    There are three ways to create an AuthSession:
        - parse username & password directly into method
        - create a /bigbang/config/authentication.yaml file that contains keys
        - type then into terminal when the method 'get_login_from_terminal'
            is raised
    """
    if os.path.isfile(filepath_auth):
        # read from /config/authentication.yaml
        with open(filepath_auth, "r") as stream:
            auth_key = yaml.safe_load(stream)
        username = auth_key["username"]
        password = auth_key["password"]
    else:
        # ask user for login keys
        username, password = get_login_from_terminal(username, password)

    if username is None or password is None:
        # continue without authentication
        return None
    else:
        # Start the AuthSession
        session = requests.Session()
        # Create the payload
        payload = {
            "LOGIN1": "",
            "Y": username,
            "p": password,
            "X": "",
        }
        # Post the payload to the site to log in
        session.post(url_login, data=payload)
        return session


def get_login_from_terminal(
    username: Union[str, None],
    password: Union[str, None],
    file_auth: str = directory_project + "/config/authentication.yaml",
) -> Tuple[Union[str, None]]:
    """
    Get login key from user during run time if 'username' and/or 'password' is 'None'.
    Return 'None' if no reply within 15 sec.
    """
    if username is None or password is None:
        record = True
    else:
        record = False
    if username is None:
        username = ask_for_input("Enter your Email: ")
    if password is None:
        password = ask_for_input("Enter your Password: ")
    if record and isinstance(username, str) and isinstance(password, str):
        loginkey_to_file(username, password, file_auth)
    return username, password


def ask_for_input(request: str) -> Union[str, None]:
    timeout = 15
    end_time = time.time() + timeout
    while time.time() < end_time:
        reply = input(request)
        try:
            assert isinstance(reply, str)
            break
        except Exception:
            reply = None
            continue
    return reply


def loginkey_to_file(
    username: str,
    password: str,
    file_auth: str,
) -> None:
    """Safe login key to yaml"""
    file = open(file_auth, "w")
    file.write(f"username: '{username}'\n")
    file.write(f"password: '{password}'")
    file.close()


def get_website_content(
    url: str,
    session: Optional[requests.Session] = None,
) -> Union[str, BeautifulSoup]:
    """
    Get HTML code from website

    Note
    ----
    Servers don't like it when one is sending too many requests from same
    ip address in short period of time. Therefore we need to:
        a) catch 'requests.exceptions.RequestException' errors
            (includes all possible errors to be on the safe side),
        b) safe intermediate results,
        c) continue where we left off at a later stage.
    """
    # TODO: include option to change BeautifulSoup args
    try:
        if session is None:
            sauce = requests.get(url)
            assert sauce.status_code == 200
            soup = BeautifulSoup(sauce.content, "html.parser")
        else:
            sauce = session.get(url)
            soup = BeautifulSoup(sauce.text, "html.parser")
        return soup
    except requests.exceptions.RequestException as e:
        if "A2=" in url:
            # if URL of mboxMessage
            logger.info(f"{e} for {url}.")
            return "RequestException"
        else:
            SystemExit()
