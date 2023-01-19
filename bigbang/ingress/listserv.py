import email
import logging
import os
import re
import subprocess
import time
import warnings
from collections import namedtuple
from io import BytesIO
from docx import Document
import mailbox
from mailbox import mboxMessage
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse

import numpy as np
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from bigbang.config import CONFIG

import bigbang.bigbang_io as bio
from bigbang.data_types import MailList
from bigbang.ingress import (
    AbstractMessageParser,
    AbstractMailList,
    AbstractMailListDomain,
)
from bigbang.ingress.utils import (
    get_website_content,
    set_website_preference_for_header,
    get_auth_session,
    remove_control_characters,
)
from bigbang.utils import (
    get_paths_to_files_in_directory,
    get_paths_to_dirs_in_directory,
)

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
logging.basicConfig(
    filename=directory_project + "/listserv.scraping.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


class ListservMessageParserWarning(BaseException):
    """Base class for ListservMessageParser class specific exceptions"""

    pass


class ListservMailListWarning(BaseException):
    """Base class for ListservMailList class specific exceptions"""

    pass


class ListservMailListDomainWarning(BaseException):
    """Base class for ListservMailListDomain class specific exceptions"""

    pass


class ListservMessageParser(AbstractMessageParser, email.parser.Parser):
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
        up AuthSession. You can create your own for the 3GPP mail list domain.
    session : requests.Session() object for the mail list domain website.

    Methods
    -------
    from_url()
    from_listserv_file()
    _get_header_from_html()
    _get_body_from_html()
    _get_header_from_listserv_file()
    _get_body_from_listserv_file()

    Example
    -------
    To create a Email message parser object, use the following syntax:
    >>> msg_parser = ListservMessageParser(
    >>>     website=True,
    >>>     login={"username": <your_username>, "password": <your_password>},
    >>> )

    To obtain the Email message content and return it as `mboxMessage` object,
    you need to do the following:
    >>> msg = msg_parser.from_url(
    >>>     list_name="3GPP_TSG_RAN_DRAFTS",
    >>>     url="https://list.etsi.org/scripts/wa.exe?A2=ind2010B&L=3GPP_TSG_RAN_DRAFTS&O=D&P=29883",
    >>>     fields="total",
    >>> )
    """

    empty_header = {}

    def from_listserv_file(
        self,
        list_name: str,
        file_path: str,
        header_start_line_nr: int,
        fields: str = "total",
    ) -> mboxMessage:
        """
        This method is required if the message is inside a file that was directly
        exported from LISTSERV 16.5 (e.g. by a member of 3GPP). Such files have
        an extension starting with LOG and ending with five digits.

        Parameters
        ----------
        list_name : The name of the LISTSERV Email list.
        file_path : Path to file that contains the Email list.
        header_start_line_nr : Line number in the file on which a new message starts.
        fields : Indicates whether to return 'header', 'body' or 'total'/both or
            the Email.
        """
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
            body = self._get_body_from_listserv_file(fcontent, header_end_line_nr)
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

        Parameters
        ----------
        content : The content of one LISTSERV file.
        header_start_line_nr : Line number in the file on which a new message starts.
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

        Parameters
        ----------
        content : The content of one LISTSERV-file.
        header_start_line_nr : Line number in the file on which a new message starts.
        header_end_line_nr : Line number in the file on which a new message ends.
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

        Parameters
        ----------
        content : The content of one LISTSERV-file.
        header_end_line_nr : Line number in the file on which a new message ends.
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
        """
        Lexer for the message header.

        Parameters
        ----------
        soup : HTML code from which the Email header can be obtained.

        Note
        ----
        Currently, this module encodes Chinese characters in UTF-8.
        This should be avoided. When improving this, you can use
        https://list.etsi.org/scripts/wa.exe?A2=3GPP_TSG_CT_WG4;d2c3487b.2106A&S=
        to test.
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
            # collect important info from LISTSERV header
            header = {}
            for line in text.find_all("tr"):
                key = str(line.find_all(re.compile("^b"))[0])
                key = re.search(r"<b>(.*?)<\/b>", key).group(1).lower()
                key = re.sub(r":", "", key).strip()
                if "subject" in key:
                    value = repr(str(line.find_all(re.compile("^a"))[0].text).strip())
                else:
                    try:  # Listserv 17
                        value = repr(str(line.find_all(re.compile("^div"))[0]))
                        value = re.search(r'">(.*)<\/div>', value).group(1)
                        if "content-type" in key:
                            value = value.split(";")[0]
                    except Exception:  # Listserv 16.5
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
                body_soup = get_website_content(urljoin(url_root, href_plain_text[0]))
                if body_soup == "RequestException":
                    return body_soup
                else:
                    return body_soup.find("pre").text
            elif href_html_text:
                body_soup = get_website_content(urljoin(url_root, href_html_text[0]))
                if body_soup == "RequestException":
                    return body_soup
                else:
                    return body_soup.get_text(strip=True)
        except Exception:
            logger.exception(
                f"The message body of {url} which is part of the "
                f"list {list_name} could not be loaded."
            )
            return None

    def _get_attachments_from_html(
        self, list_name: str, url: str, soup: BeautifulSoup
    ) -> Union[List[namedtuple], None]:
        """
        Lexer for the message attachment.
        This methods look first whether a attachment is available
        before it transforms the attached content into a string.
        """
        url_root = ("/").join(url.split("/")[:-2])
        a_tags = soup.select(f'a[href*="A3="][href*="{list_name}"]')
        href_html_attachment = [
            tag.get("href") for tag in a_tags if "Fvnd" in tag.get("href")
        ]
        if href_html_attachment:
            attachments = []
            urls_attachment = [urljoin(url_root, href) for href in href_html_attachment]
            for url_attachment in urls_attachment:
                filename = re.search("\%22(.*?)\%22", url_attachment).group(1)
                subtype = filename.split(".")[-1].lower()
                doc = namedtuple("attachment", "text subtype filename")
                if subtype == "docx":
                    try:
                        docx = Document(BytesIO(requests.get(url_attachment).content))
                    except Exception:
                        logger.exception(
                            f"The attachment of {url} which is part of the "
                            f"list {list_name} could not be loaded."
                        )
                        continue
                    document = ("\n").join([para.text for para in docx.paragraphs])
                    document = remove_control_characters(document)
                    attachments.append(
                        doc(text=document, subtype=subtype, filename=filename)
                    )
            return attachments
        else:
            return None


class ListservMailList(AbstractMailList):
    """
    This class handles the scraping of a all public Emails contained in a single
    mailing list in the LISTSERV 16.5 and 17 format.
    To be more precise, each contributor to a mailing list sends
    their message to an Email address that has the following structure:
    <mailing_list_name>@LIST.ETSI.ORG.
    Thus, this class contains all Emails send to a specific <mailing_list_name>
    (the Email localpart, such as "3GPP_TSG_CT_WG1" or "3GPP_TSG_CT_WG3_108E_MAIN").

    Parameters
    ----------
    name : The of whom the list (e.g. 3GPP_COMMON_IMS_XFER, IEEESCO-DIFUSION, ...)
    source : Contains the information of the location of the mailing list.
        It can be either an URL where the list or a path to the file(s).
    msgs : List of mboxMessage objects


    Example
    -------
    To scrape a Listserv mailing list from an URL and store it in
    run-time memory, we do the following
    >>> mlist = ListservMailList.from_url(
    >>>     name="IEEE-TEST",
    >>>     url="https://listserv.ieee.org/cgi-bin/wa?A0=IEEE-TEST",
    >>>     select={
    >>>         "years": 2015,
    >>>         "months": "November",
    >>>         "weeks": 4,
    >>>         "fields": "header",
    >>>     },
    >>>     login={"username": <your_username>, "password": <your_password>},
    >>> )

    To save it as *.mbox file we do the following
    >>> mlist.to_mbox(path_to_file)
    """

    @classmethod
    def from_url(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = {"fields": "total"},
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[requests.Session] = None,
    ) -> "ListservMailList":
        """Docstring in `AbstractMailList`."""
        if (session is None) and (url_login is not None):
            session = get_auth_session(url_login, **login)
            session = set_website_preference_for_header(url_pref, session)
        if "fields" not in list(select.keys()):
            select["fields"] = "total"
        msg_urls = cls.get_message_urls(name, url, select)
        return cls.from_messages(
            name,
            url,
            msg_urls,
            select["fields"],
            url_login,
            url_pref,
            login,
            session,
        )

    @classmethod
    def from_messages(
        cls,
        name: str,
        url: str,
        messages: Union[List[str], MailList],
        fields: str = "total",
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
    ) -> "ListservMailList":
        """Docstring in `AbstractMailList`."""
        if not messages:
            msgs = []
        elif isinstance(messages[0], str):
            if (session is None) and (url_login is not None):
                session = get_auth_session(url_login, **login)
                session = set_website_preference_for_header(url_pref, session)
            msg_parser = ListservMessageParser(
                website=True,
                url_login=url_login,
                login=login,
                session=session,
            )
            msgs = super().get_messages_from_urls(name, messages, msg_parser, fields)
        else:
            msgs = messages
        return cls(name, url, msgs)

    @classmethod
    def from_mbox(cls, name: str, filepath: str) -> "ListservMailList":
        """Docstring in `AbstractMailList`."""
        msgs = bio.mlist_from_mbox(filepath)
        return cls(name, filepath, msgs)

    @classmethod
    def from_listserv_directories(
        cls,
        name: str,
        directorypaths: List[str],
        filedsc: str = "*.LOG?????",
        select: Optional[dict] = None,
    ) -> "ListservMailList":
        """
        This method is required if the files that contain the list messages
        were directly exported from LISTSERV 16.5 (e.g. by a member of 3GPP).
        Each mailing list has its own directory and is split over multiple
        files with an extension starting with LOG and ending with five digits.

        Parameters
        ----------
        name : Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'.
        directorypaths : List of directory paths where LISTSERV formatted
            messages are.
        filedsc : A description of the relevant files, e.g. *.LOG?????
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        """
        _filepaths = []
        # run through directories and collect all filepaths
        for directorypath in directorypaths:
            _filepaths.append(get_paths_to_files_in_directory(directorypath, filedsc))
        # flatten list of lists
        filepaths = [fp for li in _filepaths for fp in li]
        return cls.from_listserv_files(name, filepaths, select)

    @classmethod
    def from_listserv_files(
        cls,
        name: str,
        filepaths: List[str],
        select: Optional[dict] = None,
    ) -> "ListservMailList":
        """
        This method is required if the files that contain the list messages
        were directly exported from LISTSERV 16.5 (e.g. by a member of 3GPP).
        Each mailing list has its own directory and is split over multiple
        files with an extension starting with LOG and ending with five digits.
        Compared to `ListservMailList.from_listserv_directories()`, this method
        reads messages from single files, instead of all the files contained in
        a directory.

        Parameters
        ----------
        name : Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'
        filepaths : List of file paths where LISTSERV formatted messages are.
            Such files can have a file extension of the form: *.LOG1405D
        select : Selection criteria that can filter messages by:
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
            header_start_line_nrs = cls.get_line_numbers_of_header_starts(fcontent)
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
    def get_message_urls(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = None,
    ) -> List[str]:
        """
        Docstring in `AbstractMailList`.

        This routine is needed for Listserv 16.5
        """

        def get_message_urls_from_period_url(name: str, url: str) -> List[str]:
            url_root = ("/").join(url.split("/")[:-2])
            soup = get_website_content(url)
            a_tags = soup.select(f'a[href*="A2="][href*="{name}"]')
            if a_tags:
                a_tags = [urljoin(url_root, url.get("href")) for url in a_tags]
            return a_tags

        def get_message_urls_from_mlist_url(name: str, url: str) -> List[str]:
            url_root = ("/").join(url.split("/")[:-2])
            soup = get_website_content(url)
            a_tags = soup.select(f'a[href*="A2="][href*="{name}"]')
            if a_tags:
                a_tags = [urljoin(url_root, url.get("href")) for url in a_tags]
            return a_tags

        msg_urls = []
        period_urls = ListservMailList.get_period_urls(url, select)
        if len(period_urls) != 0:
            # Method for Listserv 16.5
            # run through periods
            for period_url in ListservMailList.get_period_urls(url, select):
                # run through messages within period
                for msg_url in get_message_urls_from_period_url(name, period_url):
                    msg_urls.append(msg_url)
        else:
            # Method for Listserv 17
            msg_urls = get_message_urls_from_mlist_url(name, url)
        return msg_urls

    @classmethod
    def get_period_urls(cls, url: str, select: Optional[dict] = None) -> List[str]:
        """
        All messages within a certain period
        (e.g. January 2021, Week 5).

        Parameters
        ----------
        url : URL to the LISTSERV list.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        """
        # create dictionary with key indicating period and values the url
        periods, urls_of_periods = cls.get_all_periods_and_their_urls(url)

        if any(
            period in list(select.keys()) for period in ["years", "months", "weeks"]
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

                indices = ListservMailList.get_index_of_elements_in_selection(
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
        """
        LISTSERV groups messages into weekly time bundles. This method
        obtains all the URLs that lead to the messages of each time bundle.

        Returns
        -------
        Returns a tuple of two lists that look like:
        (['April 2017,  2', 'January 2001', ...], ['ulr1', 'url2', ...])
        """
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
    def get_name_from_url(url: str) -> str:
        """Get name of mailing list."""
        return url.split("A0=")[-1]

    @classmethod
    def get_line_numbers_of_header_starts(cls, content: List[str]) -> List[int]:
        """
        By definition LISTSERV logs seperate new messages by a row
        of 73 equal signs.

        Parameters
        ----------
        content : The content of one LISTSERV file.

        Returns
        -------
        List of line numbers where header starts
        """
        return [line_nr for line_nr, line in enumerate(content) if "=" * 73 in line]


class ListservMailListDomain(AbstractMailListDomain):
    """
    This class handles the scraping of a all public Emails contained in a mail
    list domain that has the LISTSERV 16.5 and 17 format, such as 3GPP.
    To be more precise, each contributor to a mail list domain sends their message
    to an Email address that has the following structure:
    <mailing_list_name>@w3.org.
    Thus, this class contains all Emails send to <mail_list_domain_name>
    (the Email domain name). These Emails are contained in a list of
    `ListservMailList` types, such that it is known to which <mailing_list_name>
    (the Email localpart) was send.

    Parameters
    ----------
    name : The mailing list domain name (e.g. 3GPP, IEEE, ...)
    url : The URL where the mailing list domain lives
    lists : A list containing the mailing lists as `ListservMailList` types

    Methods
    -------
    All methods in the `AbstractMailListDomain` class in addition to:
    from_listserv_directory()
    get_sections()

    Example
    -------
    To scrape a Listserv mailing list domain from an URL and store it in
    run-time memory, we do the following
    >>> mlistdom = ListservMailListDomain.from_url(
    >>>     name="IEEE",
    >>>     url_root="https://listserv.ieee.org/cgi-bin/wa?",
    >>>     url_home="https://listserv.ieee.org/cgi-bin/wa?HOME",
    >>>     select={
    >>>         "years": 2015,
    >>>         "months": "November",
    >>>         "weeks": 4,
    >>>         "fields": "header",
    >>>     },
    >>>     login={"username": <your_username>, "password": <your_password>},
    >>>     instant_save=False,
    >>>     only_mlist_urls=False,
    >>> )

    To save it as *.mbox file we do the following
    >>> mlistdom.to_mbox(path_to_directory)
    """

    @classmethod
    def from_url(
        cls,
        name: str,
        url_root: str,
        url_home: str,
        select: Optional[dict] = {"fields": "total"},
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        instant_save: bool = True,
        only_mlist_urls: bool = True,
    ) -> "ListservMailListDomain":
        """Docstring in `AbstractMailList`."""
        if (session is None) and (url_login is not None):
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
        url_mailing_lists: Union[List[str], List[ListservMailList]],
        select: Optional[dict] = {"fields": "total"},
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        only_mlist_urls: bool = True,
        instant_save: Optional[bool] = True,
    ) -> "ListservMailListDomain":
        """Docstring in `AbstractMailList`."""
        if isinstance(url_mailing_lists[0], str) and only_mlist_urls is False:
            if (session is None) and (url_login is not None):
                session = get_auth_session(url_login, **login)
                session = set_website_preference_for_header(url_pref, session)
            lists = []
            for url in url_mailing_lists:
                mlist_name = ListservMailList.get_name_from_url(url)
                mlist = ListservMailList.from_url(
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
    ) -> "ListservMailListDomain":
        """
        This method is required if the files that contain the mail list domain messages
        were directly exported from LISTSERV 16.5 (e.g. by a member of 3GPP).
        Each mailing list has its own subdirectory and is split over multiple
        files with an extension starting with LOG and ending with five digits.

        Parameters
        ----------
        name : mail list domain name, such that multiple instances of
            `ListservMailListDomain` can easily be distinguished.
        directorypath : Where the `ListservMailListDomain` can be initialised.
        folderdsc : A description of the relevant folders
        filedsc : A description of the relevant files, e.g. *.LOG?????
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        """
        lists = []
        _dirpaths_to_lists = get_paths_to_dirs_in_directory(directorypath, folderdsc)
        # run through directories and collect all filepaths
        for dirpath in _dirpaths_to_lists:
            _filepaths = get_paths_to_files_in_directory(dirpath, filedsc)
            mlist = ListservMailList.from_listserv_files(
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
    ) -> "ListservMailList":
        """Docstring in `AbstractMailList`."""
        filepaths = get_paths_to_files_in_directory(directorypath, filedsc)
        lists = []
        for filepath in filepaths:
            name = filepath.split("/")[-1].split(".")[0]
            lists.append(ListservMailList.from_mbox(name, filepath))
        return cls(name, directorypath, lists)

    @staticmethod
    def get_lists_from_url(
        url_root: str,
        url_home: str,
        select: dict,
        session: Optional[str] = None,
        instant_save: bool = True,
        only_mlist_urls: bool = True,
    ) -> List[Union[ListservMailList, str]]:
        """Docstring in `AbstractMailList`."""
        archive = []
        # run through archive sections
        for url in list(ListservMailListDomain.get_sections(url_root, url_home).keys()):
            soup = get_website_content(url)
            a_tags_in_section = soup.select(
                f'a[href^="{urlparse(url).path}?A0="]',
            )

            mlist_urls = [
                urljoin(url_root, a_tag.get("href")) for a_tag in a_tags_in_section
            ]
            mlist_urls = list(set(mlist_urls))  # remove duplicates

            if only_mlist_urls:
                # collect mailing-list urls
                for mlist_url in mlist_urls:
                    name = ListservMailList.get_name_from_url(mlist_url)
                    # check if mailing list contains messages in period
                    _period_urls = ListservMailList.get_all_periods_and_their_urls(
                        mlist_url
                    )[1]
                    # check if mailing list is public
                    if len(_period_urls) > 0:
                        loops = 0
                        for _period_url in _period_urls:
                            loops += 1
                            nr_msgs = len(
                                ListservMailList.get_messages_urls(
                                    name=name, url=_period_url
                                )
                            )
                            if nr_msgs > 0:
                                archive.append(mlist_url)
                                break
            else:
                # collect mailing-list contents
                for mlist_url in mlist_urls:
                    name = ListservMailList.get_name_from_url(mlist_url)
                    mlist = ListservMailList.from_url(
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
        Get different sections of mail list domain.
        On the Listserv 16.5 website they look like:
        [3GPP] [3GPP–AT1] [AT2–CONS] [CONS–EHEA] [EHEA–ERM_] ...
        On the Listserv 17 website they look like:
        [<<][<]1-50(798)[>][>>]

        Returns
        -------
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
