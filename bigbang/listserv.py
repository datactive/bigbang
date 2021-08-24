import datetime
import email
import glob
import logging
import mailbox
import os
import re
import subprocess
import time
import warnings
from mailbox import mboxMessage
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse

import numpy as np
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup
from tqdm import tqdm

from config.config import CONFIG

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)

logging.basicConfig(
    filename=directory_project + "/listserv.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


class ListservMessageParserWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class ListservListWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class ListservArchiveWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class ListservMessageParser(email.parser.Parser):
    """
    This class handles the creation of an mailbox.mboxMessage object
    (via the from_...() methods) and its storage in various other file formats
    (via the to_...() methods) that can be saved on the local machine.

    Parameters
    ----------
    website:
    url_login:
    login:
    session:

    Methods
    -------
    from_url
    from_listserv_file
    _get_header_from_html
    _get_body_from_html
    _get_header_from_listserv_file
    _get_body_from_listserv_file
    get_datetime
    to_dict
    to_mbox

    Example
    -------
    msg = ListservMessageParser.from_url(
        list_name="3GPP_TSG_CT_WG6",
        url=url_message,
        fields="total",
    )
    """

    empty_header = {
        #"subject": None,
        #"fromname": None,
        #"fromaddr": None,
        #"toname": None,
        #"toaddr": None,
        #"date": None,
        #"contenttype": None,
    }

    def __init__(
        self,
        website=False,
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        attachurls=None
    ):
        """
        Args:
            website: Set 'True' if messages are going to be scraped from websites,
                otherwise 'False' if read from local memory.
            url_login: URL to the 'Log In' page.
            url_pref: URL to the 'Preferences'/settings page.
            login:
            session:
        """
        if website:
            if session is None:
                session = get_auth_session(url_login, **login)
                session = set_website_preference_for_header(url_pref, session)
            self.session = session
        if attachurls is None:
            attachurls = []

    def create_email_message(
        self,
        archived_at: str,
        body: str,
        **header,
    ) -> mboxMessage:
        # crea EmailMessage
        msg = email.message.EmailMessage()
        if body is not None:
            msg.set_content(body)
        for key, value in header.items():
            if "content-type" == key:
                msg.set_param("Content-Type", value)
            elif "mime-version" == key:
                msg.set_param("MIME-Version", value)
            elif "content-transfer-encoding" == key:
                msg.set_param("Content-Transfer-Encoding", value)
            else:
                msg[key] = value
        if (
            (msg["Message-ID"] is None)
            and (msg["Date"] is not None)
            and (msg["From"] is not None)
        ):
            msg["Message-ID"] = archived_at.split("/")[-1]
        # convert to EmailMessage to mboxMessage
        mbox_msg = mboxMessage(msg)
        mbox_msg.add_header("Archived-At", "<" + archived_at + ">")
        mbox_msg.add_header("Attachment Urls", str(self.attachurls))
        return mbox_msg

    def from_url(
        self,
        list_name: str,
        url: str,
        fields: str = "total",
    ) -> mboxMessage:
        """
        Args:
            list_name:
            url: URL of this Email
            fields: Indicates whether to return 'header', 'body' or
                'total'/both or the Email.
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

    def from_listserv_file(
        self,
        list_name: str,
        file_path: str,
        header_start_line_nr: int,
        fields: str = "total",
    ) -> mboxMessage:
        file = open(file_path, "r", errors="replace")
        fcontent = file.readlines()
        file.close()
        header_end_line_nr = self._get_header_end_line_nr(
            fcontent, header_start_line_nr
        )
        if fields in ["header", "total"]:
            header = self._get_header_from_listserv_file(
                fcontent, header_start_line_nr, header_end_line_nr
            )
        else:
            header = self.empty_header
        if fields in ["body", "total"]:
            body = self._get_body_from_listserv_file(
                fcontent, header_end_line_nr
            )
        else:
            body = None
        return self.create_email_message(file_path, body, **header)

    def _get_header_end_line_nr(
        self,
        content: List[str],
        header_start_line_nr: int,
    ) -> List[int]:
        """
        The header ends with the first empty line encountered.

        Args:
            content: The content of one LISTSERV-file.
            header_start_line_nr:
        """
        for lnr, lcont in enumerate(content[header_start_line_nr:]):
            if len(lcont) <= 1:
                header_end_line_nr = header_start_line_nr + lnr
                break
        return header_end_line_nr

    def _get_header_from_listserv_file(
        self,
        content: List[str],
        header_start_line_nr: int,
        header_end_line_nr: int,
    ) -> Dict[str, str]:
        """
        Lexer for the message header.

        Args:
            content: The content of one LISTSERV-file.
            header_start_line_nr:
            header_end_line_nr:
        """
        # TODO re-write using email.parser.Parser
        content = content[header_start_line_nr:header_end_line_nr]
        # collect important info from LISTSERV header
        header = {}
        for lnr in range(len(content)):
            line = content[lnr]
            # get header keyword and value
            if re.match(r"\S+:\s+\S+", line):
                key = line.split(":")[0]
                value = line.replace(key + ":", "").strip().rstrip("\n")
                # if not at the end of header
                if lnr < len(content) - 1:
                    # if header-keyword value is split over two lines
                    if not re.match(r"\S+:\s+\S+", content[lnr + 1]):
                        value += " " + content[lnr + 1].strip().rstrip("\n")
                header[key.lower()] = value
        return header

    def _get_body_from_listserv_file(
        self,
        content: List[str],
        header_end_line_nr: int,
    ) -> str:
        """
        Lexer for the message body/payload.

        Args:
            content: The content of one LISTSERV-file.
            header_end_line_nr:
        """
        # TODO re-write using email.parser.Parser
        found = False
        # find body 'position' in file
        for line_nr, line in enumerate(content[header_end_line_nr:]):
            if "=" * 73 in line:
                body_end_line_nr = line_nr + header_end_line_nr
                found = True
                break
        if not found:
            body_end_line_nr = -1
        # get body content
        body = content[header_end_line_nr:body_end_line_nr]
        # remove empty lines and join into one string
        body = ("").join([line for line in body if len(line) > 1])
        return body

    def _get_header_from_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Lexer for the message header."""
        try:
            for string in ["Subject", "SUBJECT"]:
                try:
                    _text = soup.find(
                        "b",
                        text=re.compile(r"^\b%s\b" % string),
                    )  # Sometimes this returns None!
                    text = _text.parent.parent.parent.parent#.text
                    break
                except:
                    continue
            # collect important info from LISTSERV header
            header = {}
            self.attachurls = []
            for line in text.find_all("tr"):
                key = str(line.find_all(re.compile("^b"))[0])
                key = re.search(r'<b>(.*?)<\/b>', key).group(1).lower()
                key = re.sub(r':', '', key).strip()
                if "subject" in key:
                    value = repr(str(line.find_all(re.compile("^a"))[0].text).strip())
                else:
                    try:  # Listserv 17
                        value = repr(str(line.find_all(re.compile("^div"))[0]))
                        value = re.search(r'">(.*)<\/div>', value).group(1)
                        if "content-type" in key:
                            value = value.split(';')[0]
                    except:  # Listserv 16.5
                        value = repr(str(line.find_all(re.compile("^p"))[1]))
                        value = re.search(r'<p>(.*)<\/p>', value).group(1)
                        value = value.split(' <')[0]
                value = re.sub(r'&gt;', '', value).strip()
                value = re.sub(r'&lt;', '', value).strip()
                # remove Carriage return
                value = re.sub(r'\\r', '', value).strip()
                # remove Linefeed
                value = re.sub(r'\\n', '', value).strip()
                if "parts/attachments" in key:
                    value = [a['href'] for a in line.find_all('a', href=True)]
                    if len(value) > 2:
                        del value[:2] #delete the standard attachments that are on every message
                        self.attachurls.append(value)
                        break
                    break
                elif "comments" in key:
                    key = "comments-to"
                    value = re.sub(r'To:', '', value).strip()
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
        line = (" ").join(line.split(" ")[:-1]).lstrip()
        # convert format to local version of date and time
        date_time_obj = datetime.datetime.strptime(
            line, "%a, %d %b %Y %H:%M:%S"
        )
        return date_time_obj.strftime("%c")

    @staticmethod
    def create_message_id(
        date: str,
        from_address: str,
    ) -> str:
        message_id = (".").join([date, from_address])
        # remove special characters
        message_id = re.sub(r"[^a-zA-Z0-9]+", "", message_id)
        return message_id

    @staticmethod
    def to_dict(msg: mboxMessage) -> Dict[str, str]:
        dic = {"Body": msg.get_payload()}
        for key, value in msg.items():
            dic[key] = value
        return dic

    @staticmethod
    def to_pandas_dataframe(msg: mboxMessage) -> pd.DataFrame:
        return pd.DataFrame(
            ListservMessageParser.to_dict(msg),
            index=[msg["Message-ID"]],
        )

    @staticmethod
    def to_mbox(msg: mboxMessage, filepath: str, mode: str = "w"):
        """
        Safe mail list to .mbox files.
        """
        if Path(filepath).is_file():
            Path(filepath).unlink()
        mbox = mailbox.mbox(filepath)
        mbox.lock()
        mbox.add(msg)
        mbox.flush()
        mbox.unlock()


class ListservList:
    """
    This class handles a single mailing list of a public archive in the
    LISTSERV 16.5 format.

    Parameters
    ----------
    name
        The of whom the list (e.g. 3GPP_COMMON_IMS_XFER, IEEESCO-DIFUSION, ...)
    source
        Contains the information of the location of the mailing list.
        It can be either an URL where the list or a path to the file(s).
    msgs
        List of mboxMessage objects

    Methods
    -------
    from_url
    from_messages
    from_mbox
    from_listserv_files
    from_listserv_directories
    get_messages_from_url
    get_message_urls
    get_period_urls
    get_line_numbers_of_header_starts
    get_index_of_elements_in_selection
    to_dict
    to_pandas_dataframe
    to_mbox

    Example
    -------
    mlist = ListservList.from_url(
        "3GPP_TSG_CT_WG6",
        url="https://list.etsi.org/scripts/wa.exe?A0=3GPP_TSG_CT_WG6",
        select={
            "years": (2020, 2021),
            "months": "January",
            "weeks": [1,5],
            "fields": "header",
        },
    )
    """

    def __init__(
        self,
        name: str,
        source: Union[List[str], str],
        msgs: List[mboxMessage],
    ):
        self.name = name
        self.source = source
        self.messages = msgs

    def __len__(self) -> int:
        return len(self.messages)

    def __iter__(self):
        return iter(self.messages)

    def __getitem__(self, index) -> mboxMessage:
        return self.messages[index]

    @classmethod
    def from_url(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = None,
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
    ) -> "ListservList":
        """
        Args:
            name: Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'
            url: URL to the LISTSERV list.
            select: Selection criteria that can filter messages by:
                - content, i.e. header and/or body
                - period, i.e. written in a certain year, month, week-of-month
            url_login: URL to the 'Log In' page
            url_pref: URL to the 'Preferences'/settings page
        """
        if session is None:
            session = get_auth_session(url_login, **login)
            session = set_website_preference_for_header(url_pref, session)
        if select is None:
            select = {"fields": "total"}
        elif "fields" not in list(select.keys()):
            select["fields"] = "total"
        msgs = cls.get_messages_from_url(name, url, select, session)
        return cls.from_messages(name, url, msgs)

    @classmethod
    def from_messages(
        cls,
        name: str,
        url: str,
        messages: List[Union[str, mboxMessage]],
        fields: str = "total",
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
    ) -> "ListservList":
        """
        Args:
            messages: Can either be a list of URLs to specific LISTSERV messages
                or a list of `mboxMessage` objects.
            url_login: URL to the 'Log In' page.
            url_pref: URL to the 'Preferences'/settings page.
        """
        if not messages:
            # create empty ListservList for ListservArchive
            msgs = messages
        elif isinstance(messages[0], str):
            # create ListservList from message URLs
            msgs = []
            msg_parser = ListservMessageParser(
                website=True,
                url_login=url_login,
                login=login,
            )
            for msg_url in tqdm(messages, ascii=True, desc=name):
                msg = msg_parser.from_url(
                    list_name=name,
                    url=msg_url,
                    fields=fields,
                )
                if msg.get_payload() == "RequestException":
                    time.sleep(30)
                else:
                    msgs.append(msg)
                    logger.info(f"Recorded the message {msg_url}.")
        else:
            # create ListservList from list of mboxMessage
            msgs = messages
        return cls(name, url, msgs)

    @classmethod
    def from_mbox(
        cls,
        name: str,
        filepath: str,
    ) -> "ListservList":
        box = mailbox.mbox(filepath, create=False)
        msgs = list(box.values())
        return cls(name, filepath, msgs)

    @classmethod
    def from_listserv_directories(
        cls,
        name: str,
        directorypaths: List[str],
        filedsc: str = "*.LOG?????",
        select: Optional[dict] = None,
    ) -> "ListservList":
        """
        Args:
            name: Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'.
            directorypaths: List of directory paths where LISTSERV formatted
                messages are.
            filedsc: A description of the relevant files, e.g. *.LOG?????
            select: Selection criteria that can filter messages by:
                - content, i.e. header and/or body
                - period, i.e. written in a certain year, month, week-of-month
        """
        _filepaths = []
        # run through directories and collect all filepaths
        for directorypath in directorypaths:
            _filepaths.append(
                get_paths_to_files_in_directory(directorypath, filedsc)
            )
        # flatten list of lists
        filepaths = [fp for li in _filepaths for fp in li]
        return cls.from_listserv_files(name, filepaths, select)

    @classmethod
    def from_listserv_files(
        cls,
        name: str,
        filepaths: List[str],
        select: Optional[dict] = None,
    ) -> "ListservList":
        """
        Args:
            name: Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'
            filepaths: List of file paths where LISTSERV formatted messages are.
                Such files can have a file extension of the form: *.LOG1405D
            select: Selection criteria that can filter messages by:
                - content, i.e. header and/or body
                - period, i.e. written in a certain year, month, week-of-month
        """
        if select is None:
            select = {"fields": "total"}
        msgs = []
        for filepath in filepaths:
            # TODO: implement selection filter
            file = open(filepath, "r", errors="replace")
            fcontent = file.readlines()
            # get positions of all Emails in file
            header_start_line_nrs = cls.get_line_numbers_of_header_starts(
                fcontent
            )
            file.close()
            # run through all messages in file
            msg_parser = ListservMessageParser(website=False)
            for msg_nr in header_start_line_nrs:
                msgs.append(
                    msg_parser.from_listserv_file(
                        name,
                        filepath,
                        msg_nr,
                        select["fields"],
                    )
                )
        return cls(name, filepaths, msgs)
    
    @classmethod
    def get_messages_from_url(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = None,
        session: Optional[dict] = None,
    ) -> List[mboxMessage]:
        """
        Generator that returns all messages within a certain period
        (e.g. January 2021, Week 5).

        Args:
            name: Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'
            url: URL to the LISTSERV list.
            select: Selection criteria that can filter messages by:
                - content, i.e. header and/or body
                - period, i.e. written in a certain year, month, week-of-month
            session: AuthSession
        """
        # get all message URLs
        msg_urls = cls.get_message_urls(name, url, select)
        msg_parser = ListservMessageParser(website=True, session=session)
        # get all message contents
        msgs = []
        for msg_url in tqdm(msg_urls, ascii=True, desc=name):
            msg = msg_parser.from_url(
                list_name=name,
                url=msg_url,
                fields=select["fields"],
            )
            if msg.get_payload() == "RequestException":
                time.sleep(30)
            else:
                msgs.append(msg)
                logger.info(f"Recorded the message {msg_url}.")
            # wait between loading messages, for politeness
            time.sleep(1)
        return msgs
    
    @classmethod
    def get_message_urls(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = None,
    ) -> List[str]:
        """
        Args:
            name: Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'
            url: URL to the LISTSERV list.
            select: Selection criteria that can filter messages by:
                - content, i.e. header and/or body
                - period, i.e. written in a certain year, month, week-of-month
        
        Returns:
            List of all selected URLs of the messages in the mailing list.
        """
        if select is None:
            select = {"fields": "total"}
        msg_urls = []
        # run through periods
        for period_url in ListservList.get_period_urls(url, select):
            # run through messages within period
            for msg_url in ListservList.get_messages_urls(name, period_url):
                msg_urls.append(msg_url)
        return msg_urls

    @classmethod
    def get_period_urls(
        cls, url: str, select: Optional[dict] = None
    ) -> List[str]:
        """
        All messages within a certain period
        (e.g. January 2021, Week 5).
        """
        # create dictionary with key indicating period and values the url
        periods, urls_of_periods = cls.get_all_periods_and_their_urls(url)

        if any(
            period in list(select.keys())
            for period in ["years", "months", "weeks"]
        ):
            for key, value in select.items():
                if key == "years":
                    cond = lambda x: int(re.findall(r"\d{4}", x)[0])
                elif key == "months":
                    cond = lambda x: x.split(" ")[0]
                elif key == "weeks":
                    cond = lambda x: int(x.split(" ")[-1])
                else:
                    continue

                periodquants = [cond(period) for period in periods]

                indices = ListservList.get_index_of_elements_in_selection(
                    periodquants,
                    urls_of_periods,
                    value,
                )

                periods = [periods[idx] for idx in indices]
                urls_of_periods = [urls_of_periods[idx] for idx in indices]
        return urls_of_periods

    @staticmethod
    def get_all_periods_and_their_urls(
        url: str,
    ) -> Tuple[List[str], List[str]]:
        # wait between loading messages, for politeness
        time.sleep(0.5)
        
        url_root = ("/").join(url.split("/")[:-2])
        soup = get_website_content(url)
        periods = [list_tag.find("a").text for list_tag in soup.find_all("li")]
        urls_of_periods = [
            urljoin(url_root, list_tag.find("a").get("href"))
            for list_tag in soup.find_all("li")
        ]
        return periods, urls_of_periods
    
    @staticmethod
    def get_index_of_elements_in_selection(
        times: List[Union[int, str]],
        urls: List[str],
        filtr: Union[tuple, list, int, str],
    ) -> List[int]:
        """
        Filter out messages that where in a specific period. Period here is a set
        containing units of year, month, and week-of-month which can have the following
        example elements:
            - years: (1992, 2010), [2000, 2008], 2021
            - months: ["January", "July"], "November"
            - weeks: (1, 4), [1, 5], 2

        Args:
            times: A list containing information of the period for each
                group of mboxMessage.
            urls: Corresponding URLs of each group of mboxMessage of which the
                period info is contained in `times`.
            filtr: Containing info on what should be filtered.

        Returns:
            Indices of to the elements in `times`/`ursl`.
        """
        if isinstance(filtr, tuple):
            # filter year or week in range
            cond = lambda x: (np.min(filtr) <= x <= np.max(filtr))
        if isinstance(filtr, list):
            # filter in year, week, or month in list
            cond = lambda x: x in filtr
        if isinstance(filtr, int):
            # filter specific year or week
            cond = lambda x: x == filtr
        if isinstance(filtr, str):
            # filter specific month
            cond = lambda x: x == filtr
        return [idx for idx, time in enumerate(times) if cond(time)]
    
    @staticmethod
    def get_name_from_url(url: str) -> str:
        """ Get name of mailing list. """
        return url.split("A0=")[-1]

    @classmethod
    def get_messages_urls(cls, name: str, url: str) -> List[str]:
        """
        Args:
            name: Name of the `ListservList`
            url: URL to group of messages that are within the same period.

        Returns:
            List to URLs from which`mboxMessage` can be initialized.
        """
        tstart = time.time()
        url_root = ("/").join(url.split("/")[:-2])
        soup = get_website_content(url)
        a_tags = soup.select(f'a[href*="A2="][href*="{name}"]')
        if a_tags:
            a_tags = [urljoin(url_root, url.get("href")) for url in a_tags]
        return a_tags

    @classmethod
    def get_line_numbers_of_header_starts(
        cls, content: List[str]
    ) -> List[int]:
        """
        By definition LISTSERV logs seperate new messages by a row
        of 73 equal signs.

        Args:
            content: The content of one LISTSERV-file.

        Returns:
            List of line numbers where header starts
        """
        return [
            line_nr for line_nr, line in enumerate(content) if "=" * 73 in line
        ]

    def to_pandas_dataframe(self) -> pd.DataFrame:
        msg_parser = ListservMessageParser()
        # run through messages
        first = True
        for msg in self.messages:
            df = msg_parser.to_pandas_dataframe(msg)
            if first:
                dfsum = df
                first = False
            else:
                dfsum = dfsum.append(df, ignore_index=False)
        return dfsum

    def to_dict(self) -> Dict[str, List[str]]:
        """
        Place all message into a dictionary.
        """
        return self.to_pandas_dataframe().to_dict()

    def to_mbox(self, dir_out: str, filename: Optional[str] = None):
        """
        Safe mailing list to .mbox files.

        Args:
        """
        # create filepath
        if filename is None:
            filepath = f"{dir_out}/{self.name}.mbox"
        else:
            filepath = f"{dir_out}/{filename}.mbox"
        # delete file if there is one at the filepath
        if Path(filepath).is_file():
            Path(filepath).unlink()
        mbox = mailbox.mbox(filepath)
        mbox.lock()
        for msg in self.messages:
            try:
                mbox.add(msg)
            except Exception as e:
                logger.info(
                    f'Add to .mbox error for {msg["Archived-At"]} because, {e}'
                )
        mbox.flush()
        mbox.unlock()
        logger.info(f"The list {self.name} is saved at {filepath}.")

        mbox.lock()
        mbox.add(msg)
        mbox.flush()
        mbox.unlock()


class ListservArchive(object):
    """
    This class handles a public mailing list archive that uses the
    LISTSERV 16.5 format.
    An archive is a list of ListservList elements.

    Parameters
    ----------
    name
        The of whom the archive is (e.g. 3GPP, IEEE, ...)
    url
        The URL where the archive lives
    lists
        A list containing the mailing lists as `ListservList` types

    Methods
    -------
    from_url
    from_mbox
    from_mailing_lists
    from_listserv_directory
    get_lists
    get_sections
    to_dict
    to_pandas_dataframe
    to_mbox

    Example
    -------
    arch = ListservArchive.from_url(
        "3GPP",
        "https://list.etsi.org/scripts/wa.exe?",
        "https://list.etsi.org/scripts/wa.exe?HOME",
        select={
            "years": (2020, 2021),
            "months": "January",
            "weeks": [1,5],
            "fields": "header",
        },
    )
    """

    def __init__(self, name: str, url: str, lists: List[Union[ListservList, str]]):
        self.name = name
        self.url = url
        self.lists = lists

    def __len__(self):
        return len(self.lists)

    def __iter__(self):
        return iter(self.lists)

    def __getitem__(self, index):
        return self.lists[index]

    @classmethod
    def from_url(
        cls,
        name: str,
        url_root: str,
        url_home: str,
        select: Optional[dict] = None,
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        instant_save: bool = True,
        only_mlist_urls: bool = True,
    ) -> "ListservArchive":
        """
        Create ListservArchive from a given URL.

        Args:
            name:
            url_root:
            url_home:
            select: Selection criteria that can filter messages by:
                - content, i.e. header and/or body
                - period, i.e. written in a certain year, month, week-of-month
            url_login: URL to the 'Log In' page.
            url_pref: URL to the 'Preferences'/settings page.
            login: login keys {"username": str, "password": str}
            session: if auth-session was already created externally
            instant_save: Boolean giving the choice to save a `ListservList` as
                soon as it is completely scraped or collect entire archive. The
                prior is recommended if a large number of mailing lists are
                scraped which can require a lot of memory and time.
            only_list_urls: Boolean giving the choice to collect only `ListservList`
                URLs or also their contents.
        """
        if session is None:
            session = get_auth_session(url_login, **login)
            session = set_website_preference_for_header(url_pref, session)
        lists = cls.get_lists_from_url(
            url_root,
            url_home,
            select,
            session,
            instant_save,
            only_mlist_urls,
        )
        return cls.from_mailing_lists(
            name,
            url_root,
            lists,
            select,
            session,
            only_mlist_urls,
        )

    @classmethod
    def from_mailing_lists(
        cls,
        name: str,
        url_root: str,
        url_mailing_lists: Union[List[str], List[ListservList]],
        select: Optional[dict] = None,
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        only_mlist_urls: bool = True,
        instant_save: Optional[bool] = True,
    ) -> "ListservArchive":
        """
        Create ListservArchive from a given list of 'ListservList'.

        Args:
            name: Name used for folder in which scraped lists will be stored.
            url_root:
            url_mailing_lists:
            url_login: URL to the 'Log In' page.
            url_pref: URL to the 'Preferences'/settings page.

        """
        if isinstance(url_mailing_lists[0], str) and only_mlist_urls is False:
            if session is None:
                session = get_auth_session(url_login, **login)
                session = set_website_preference_for_header(url_pref, session)
            lists = []
            for url in url_mailing_lists:
                mlist_name = url.split("A0=")[-1]
                mlist = ListservList.from_url(
                    name=mlist_name,
                    url=url,
                    select=select,
                    session=session,
                )
                if len(mlist) != 0:
                    if instant_save:
                        dir_out = CONFIG.mail_path + name
                        Path(dir_out).mkdir(parents=True, exist_ok=True)
                        mlist.to_mbox(dir_out=dir_out)
                    else:
                        logger.info(f"Recorded the list {mlist.name}.")
                        lists.append(mlist)
        else:
            lists = url_mailing_lists
        return cls(name, url_root, lists)

    @classmethod
    def from_listserv_directory(
        cls,
        name: str,
        directorypath: str,
        folderdsc: str = "*",
        filedsc: str = "*.LOG?????",
        select: Optional[dict] = None,
    ) -> "ListservArchive":
        """
        Args:
            name: Name of the archive, e.g. '3GPP'.
            directorypath: Where the ListservArchive can be initialised.
            folderdsc: A description of the relevant folders
            filedsc: A description of the relevant files, e.g. *.LOG?????
            select: Selection criteria that can filter messages by:
                - content, i.e. header and/or body
                - period, i.e. written in a certain year, month, week-of-month
        """
        lists = []
        _dirpaths_to_lists = get_paths_to_dirs_in_directory(
            directorypath, folderdsc
        )
        # run through directories and collect all filepaths
        for dirpath in _dirpaths_to_lists:
            _filepaths = get_paths_to_files_in_directory(dirpath, filedsc)
            mlist = ListservList.from_listserv_files(
                dirpath.split("/")[-2],
                _filepaths,
                select,
            )
            lists.append(mlist)
        return cls(name, directorypath, lists)

    @classmethod
    def from_mbox(
        cls,
        name: str,
        directorypath: str,
        filedsc: str = "*.mbox",
    ) -> "ListservArchive":
        filepaths = get_paths_to_files_in_directory(directorypath, filedsc)
        lists = []
        for filepath in filepaths:
            name = filepath.split("/")[-1].split(".")[0]
            lists.append(ListservList.from_mbox(name, filepath))
        return cls(name, directorypath, lists)

    @staticmethod
    def get_lists_from_url(
        url_root: str,
        url_home: str,
        select: dict,
        session: Optional[str] = None,
        instant_save: bool = True,
        only_mlist_urls: bool = True,
    ) -> List[Union[ListservList, str]]:
        """
        Created dictionary of all lists in the archive.

        Args:

        Returns:
            archive_dict: the keys are the names of the lists and the value their url
        """
        archive = []
        # run through archive sections
        for url in list(
            ListservArchive.get_sections(url_root, url_home).keys()
        ):
            soup = get_website_content(url)
            a_tags_in_section = soup.select(
                f'a[href^="{urlparse(url).path}?A0="]',
            )

            mlist_urls = [
                urljoin(url_root, a_tag.get("href"))
                for a_tag in a_tags_in_section
            ]
            mlist_urls = list(set(mlist_urls))  # remove duplicates

            if only_mlist_urls:
                # collect mailing-list urls
                for mlist_url in mlist_urls:
                    name = ListservList.get_name_from_url(mlist_url)
                    # check if mailing list contains messages in period
                    _period_urls = ListservList.get_all_periods_and_their_urls(
                        mlist_url
                    )[1]
                    # check if mailing list is public
                    if len(_period_urls) > 0:
                        loops = 0
                        for _period_url in _period_urls:
                            loops += 1
                            nr_msgs = len(
                                ListservList.get_messages_urls(
                                    name=name, url=_period_url
                                )
                            )
                            if nr_msgs > 0:
                                archive.append(mlist_url)
                                break
            else:
                # collect mailing-list contents
                for mlist_url in mlist_urls:
                    name = ListservList.get_name_from_url(mlist_url)
                    mlist = ListservList.from_url(
                        name=name,
                        url=mlist_url,
                        select=select,
                        session=session,
                    )
                    if len(mlist) != 0:
                        if instant_save:
                            dir_out = CONFIG.mail_path + name
                            Path(dir_out).mkdir(parents=True, exist_ok=True)
                            mlist.to_mbox(dir_out=CONFIG.mail_path)
                            archive.append(mlist.name)
                        else:
                            logger.info(f"Recorded the list {mlist.name}.")
                            archive.append(mlist)
        return archive

    def get_sections(url_root: str, url_home: str) -> int:
        """
        Get different sections of archive.
        On the Listserv 16.5 website they look like:
        [3GPP] [3GPP–AT1] [AT2–CONS] [CONS–EHEA] [EHEA–ERM_] ...
        On the Listserv 17 website they look like:
        [<<][<]1-50(798)[>][>>]

        Returns:
            If sections exist, it returns their urls and names. Otherwise it returns
            the url_home.
        """
        soup = get_website_content(url_home)
        sections = soup.select(
            'a[href*="INDEX="][href*="p="]',
        )
        archive_sections_dict = {}
        if sections:
            for sec in sections:
                key = urljoin(url_root, sec.get("href"))
                value = sec.text
                if value in ["Next", "Previous"]:
                    continue
                archive_sections_dict[key] = value
            archive_sections_dict[re.sub(r"p=[0-9]+", "p=1", key)] = "FIRST"
        else:
            archive_sections_dict[url_home] = "Home"
        return archive_sections_dict

    def to_conversationkg_dict(self) -> Dict[str, List[str]]:
        """
        Place all message in all lists into a dictionary of the form:
            dic = {
                "message_ID1": {
                    "body": ...,
                    "subject": ...,
                    ... ,
                }
                "message_ID2": {
                    "body": ...,
                    "subject": ...,
                    ... ,
                }
            }
        """
        # initialize dictionary
        dic = {}
        msg_nr = 0
        # run through lists
        for mlist in self.lists:
            # run through messages
            for msg in mlist.messages:
                dic[f"ID{msg_nr}"] = msg.to_dict()
                msg_nr += 1
        return dic

    def to_pandas_dataframe(self) -> pd.DataFrame:
        # run through lists
        first = True
        for mlist in self.lists:
            df = mlist.to_pandas_dataframe()
            if first:
                dfsum = df
                first = False
            else:
                dfsum = dfsum.append(df, ignore_index=False)
        return dfsum

    def to_dict(self) -> Dict[str, List[str]]:
        """
        Place all message into a dictionary.
        """
        return self.to_pandas_dataframe().to_dict()

    def to_mbox(self, dir_out: str):
        """
        Save Archive content to .mbox files
        """
        for llist in self.lists:
            llist.to_mbox(dir_out)


def set_website_preference_for_header(
    url_pref: str, session: requests.Session,
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

    Note: LISTSERV 16.5 archives don't like it when one is sending too many
    requests from same ip address in short period of time. Therefore we need
    to:
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


def get_paths_to_files_in_directory(
    directory: str, file_dsc: str = "*"
) -> List[str]:
    """Get paths of all files matching file_dsc in directory"""
    template = f"{directory}{file_dsc}"
    file_paths = glob.glob(template)
    return file_paths


def get_paths_to_dirs_in_directory(
    directory: str, folder_dsc: str = "*"
) -> List[str]:
    """Get paths of all directories matching file_dsc in directory"""
    template = f"{directory}{folder_dsc}"
    dir_paths = glob.glob(template)
    # normalize directory paths
    dir_paths = [dir_path + "/" for dir_path in dir_paths]
    return dir_paths
