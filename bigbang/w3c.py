import numpy as np
import email
from tqdm import tqdm
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

from config.config import CONFIG

from bigbang.bigbang_io import MessageIO, ListIO, ArchiveIO
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
        otherwise 'False' if read from local memory. This distinction needs to
        be made if missing messages should be added.
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
    >>> msg_parser = W3CMessageParser(website=True)

    To obtain the Email message content and return it as `mboxMessage` object,
    you need to do the following:
    >>> msg = msg_parser.from_url(
    >>>     list_name="public-2018-permissions-ws",
    >>>     url="https://lists.w3.org/Archives/Public/public-2018-permissions-ws/2019May/0000.html",
    >>>     fields="total",
    >>> )
    """

    empty_header = {}

    def __init__(
        self,
        url_login: str = None,
        url_pref: str = None,
        website: bool = False,
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[requests.Session] = None,
    ):
        if website:
            if (session is None) and (url_login is not None):
                session = get_auth_session(url_login, **login)
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
                body = self._get_body_from_html(url, soup)
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
        header = {
            "message-ID": "#message-id",
            "Date": "#date",
            "To": "#to",
            "Cc": "#cc",
        }
        for key, value in header.items():
            try:
                header[key] = parse_dfn_header(
                    text_for_selector(soup, value)
                ).strip()
            except Exception:
                header[key] = ""
                continue
        header["Subject"] = text_for_selector(soup, "h1")

        from_text = parse_dfn_header(text_for_selector(soup, "#from"))
        from_name = from_text.split("<")[0].strip()
        from_address = text_for_selector(soup, "#from a")
        header["From"] = email.utils.formataddr(
            (from_name, email.header.Header(from_address).encode())
        )

        in_reply_to_pattern = re.compile('<!-- inreplyto="(.+?)"')
        match = in_reply_to_pattern.search(str(soup))
        if match:
            header["In-Reply-To"] = "<" + match.groups()[0] + ">"

        return header

    def _get_body_from_html(
        self, url: str, soup: BeautifulSoup
    ) -> Union[str, None]:
        """
        Lexer for the message body/payload.
        This methods assumes that the body is available in text/plain.

        Parameters
        ----------
        url : URL to the Email message.
        soup : HTML code from which the Email body can be obtained.
        """
        # TODO re-write using email.parser.Parser
        try:
            return text_for_selector(soup, "#body")
        except Exception:
            logger.info(f"The message body of {url} could not be loaded.")
            return None

    @staticmethod
    def get_datetime(line: str) -> str:
        """
        Parameters
        ----------
        line : String that contains date and time.
        """
        dt = (" ").join(line.split(" ")[:-1]).lstrip()
        # convert format to local version of date and time
        date_time_obj = datetime.datetime.strptime(
            dt, "%a, %d %b %Y %H:%M:%S %z"
        )
        return date_time_obj.strftime("%a, %d %b %Y %H:%M:%S %z")

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
        return MessageIO.to_dict(msg)

    @staticmethod
    def to_pandas_dataframe(msg: mboxMessage) -> pd.DataFrame:
        """Convert mboxMessage to a pandas.DataFrame"""
        return MessageIO.to_pandas_dataframe(msg)

    @staticmethod
    def to_mbox(msg: mboxMessage, filepath: str):
        """
        Parameters
        ----------
        msg : The Email.
        filepath : Path to file in which the Email will be stored.
        """
        return MessageIO.to_mbox(msg, filepath)


class W3CList(ListIO):
    """
    This class handles the scraping of a single W3C mailing list.

    Parameters
    ----------
    name : The name of the list (e.g. public-2018-permissions-ws, ...)
    source : Contains the information of the location of the mailing list.
        It can be either an URL where the list or a path to the file(s).
    msgs : List of mboxMessage objects

    Methods
    -------
    from_url()
    from_messages()
    from_mbox()
    get_messages_from_url()
    get_message_urls()
    get_period_urls()
    get_index_of_elements_in_selection()
    to_dict()
    to_pandas_dataframe()
    to_mbox()


    Example
    -------
    To scrape a W3C mailing list from an URL and store it in
    run-time memory, we do the following
    >>> mlist = W3CList.from_url(
    >>>     name="public-bigdata",
    >>>     url="https://lists.w3.org/Archives/Public/public-bigdata/",
    >>>     select={
    >>>         "years": 2015,
    >>>         "months": "August",
    >>>         "fields": "header",
    >>>     },
    >>> )

    To save it as *.mbox file we do the following
    >>> mlist.to_mbox(path_to_file)
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
        """Get number of messsages within the mailing list."""
        return len(self.messages)

    def __iter__(self):
        """Iterate over each message within the mailing list."""
        return iter(self.messages)

    def __getitem__(self, index: int) -> mboxMessage:
        """Get specific message at position `index` within the mailing list."""
        return self.messages[index]

    @classmethod
    def from_url(
        cls,
        name: str,
        url: str,
        url_login: str = None,
        url_pref: str = None,
        select: Optional[dict] = None,
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[requests.Session] = None,
    ) -> "W3CList":
        """
        Parameters
        ----------
        name : Name of the list of messages, e.g. 'public-bigdata'
        url : URL to the W3C list.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year and month
        url_login : URL to the 'Log In' page
        url_pref : URL to the 'Preferences'/settings page
        login : Login credentials (username and password) that were used to set
            up AuthSession.
        session : requests.Session() object for the Email archive website.
        """
        if (session is None) and (url_login is not None):
            session = get_auth_session(url_login, **login)
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
        url_login: str = None,
        url_pref: str = None,
        fields: str = "total",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
    ) -> "W3CList":
        """
        Parameters
        ----------
        name : Name of the list of messages, e.g. 'public-bigdata'
        url : URL to the W3C Email list.
        messages : Can either be a list of URLs to specific W3C messages
            or a list of `mboxMessage` objects.
        url_login : URL to the 'Log In' page.
        url_pref : URL to the 'Preferences'/settings page.
        login : Login credentials (username and password) that were used to set
            up AuthSession. You can create your own for the W3C archive.
        session : requests.Session() object for the W3C Email archive website.
        """
        if not messages:
            # create empty W3CList for W3CArchive
            msgs = messages
        elif isinstance(messages[0], str):
            # create W3CList from message URLs
            msgs = []
            msg_parser = W3CMessageParser(
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
            # create W3CList from list of mboxMessage
            msgs = messages
        return cls(name, url, msgs)

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

        Parameters
        ----------
        name : Name of the list of messages, e.g. 'public-bigdata'
        url : URL to the W3C list.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year and month
        session : requests.Session() object for the W3C Email archive website.
        """
        # get all message URLs
        msg_urls = cls.get_message_urls(name, url, select)
        msg_parser = W3CMessageParser(website=True, session=session)
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
        Parameters
        ----------
        name : Name of the list of messages, e.g. 'public-bigdata'
        url : URL to the W3C list.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year and month

        Returns
        -------
        List of all selected URLs of the messages in the mailing list.
        """
        if select is None:
            select = {"fields": "total"}
        msg_urls = []
        # run through periods
        for period_url in W3CList.get_period_urls(url, select):
            # run through messages within period
            for msg_url in W3CList.get_messages_urls(name, period_url):
                msg_urls.append(msg_url)
        return msg_urls

    @classmethod
    def get_period_urls(
        cls, url: str, select: Optional[dict] = None
    ) -> List[str]:
        """
        All messages within a certain period (e.g. January 2021).

        Parameters
        ----------
        url : URL to the W3C list.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year and month
        """
        # create dictionary with key indicating period and values the url
        periods, urls_of_periods = cls.get_all_periods_and_their_urls(url)

        if any(
            period in list(select.keys()) for period in ["years", "months"]
        ):
            for key, value in select.items():
                if key == "years":
                    cond = lambda x: int(re.findall(r"\d{4}", x)[0])
                elif key == "months":
                    cond = lambda x: x.split(" ")[0]
                else:
                    continue

                periodquants = [cond(period) for period in periods]

                indices = W3CList.get_index_of_elements_in_selection(
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
        W3C groups messages into monthly time bundles. This method
        obtains all the URLs that lead to the messages of each time bundle.

        Returns
        -------
        Returns a tuple of two lists that look like:
        (['April 2017', 'January 2001', ...], ['ulr1', 'url2', ...])
        """
        # wait between loading messages, for politeness
        time.sleep(0.5)
        soup = get_website_content(url)
        periods = []
        urls_of_periods = []
        rows = soup.select("tbody tr")
        for row in rows:
            link = row.select("td:nth-of-type(1) a")[0]
            periods.append(link.text)
            urls_of_periods.append(url + link.get("href"))
        return periods, urls_of_periods

    @staticmethod
    def get_index_of_elements_in_selection(
        times: List[Union[int, str]],
        urls: List[str],
        filtr: Union[tuple, list, int, str],
    ) -> List[int]:
        """
        Filter out messages that where in a specific period. Period here is a set
        containing units of year and month which can have the following
        example elements:
            - years: (1992, 2010), [2000, 2008], 2021
            - months: ["January", "July"], "November"

        Parameters
        ----------
        times : A list containing information of the period for each
            group of mboxMessage.
        urls : Corresponding URLs of each group of mboxMessage of which the
            period info is contained in `times`.
        filtr : Containing info on what should be filtered.

        Returns
        -------
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

    @classmethod
    def get_messages_urls(cls, name: str, url: str) -> List[str]:
        """
        Parameters
        ----------
        name : Name of the W3C mailing list.
        url : URL to group of messages that are within the same period.

        Returns
        -------
        List to URLs from which `mboxMessage` can be initialized.
        """
        soup = get_website_content(url)
        a_tags = soup.select("div.messages-list a")
        if a_tags:
            a_tags = [
                urljoin(url, a_tag.get("href"))
                for a_tag in a_tags
                if a_tag.get("href") is not None
            ]
        return a_tags

    def to_dict(self, include_body: bool = True) -> Dict[str, List[str]]:
        """
        Parameters
        ----------
        include_body : A boolean that indicates whether the message body should
            be included or not.

        Returns
        -------
        A Dictionary with the first key layer being the header field names and
        the "body" key. Each value field is a list containing the respective
        header field contents arranged by the order as they were scraped from
        the web. This format makes the conversion to a pandas.DataFrame easier.
        """
        return ListIO.to_dict(self.messages, include_body)

    def to_pandas_dataframe(self, include_body: bool = True) -> pd.DataFrame:
        """
        Parameters
        ----------
        include_body : A boolean that indicates whether the message body should
            be included or not.

        Returns
        -------
        Converts the mailing list into a pandas.DataFrame object in which each
        row represents an Email.
        """
        return ListIO.to_pandas_dataframe(self.messages, include_body)

    def to_mbox(self, dir_out: str, filename: Optional[str] = None):
        """Safe mailing list to .mbox files."""
        if filename is None:
            ListIO.to_mbox(self.messages, dir_out, self.name)
        else:
            ListIO.to_mbox(self.messages, dir_out, filename)


class W3CArchive(object):
    """
    This class handles the scraping of W3C public mailing list archive in the
    hypermail format.

    Parameters
    ----------
    name : The name of the archive.
    url : The URL where the archive lives
    lists : A list containing the mailing lists as `W3CList` types

    Methods
    -------
    from_url()
    from_mbox()
    from_mailing_lists()
    from_listserv_directory()
    get_lists()
    get_sections()
    to_dict()
    to_pandas_dataframe()
    to_mbox()

    Example
    -------
    To scrape a W3C mailing list archive from an URL and store it in
    run-time memory, we do the following
    >>> arch = W3CArchive.from_url(
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
    >>> arch.to_mbox(path_to_directory)
    """

    def __init__(self, name: str, url: str, lists: List[Union[W3CList, str]]):
        self.name = name
        self.url = url
        self.lists = lists

    def __len__(self):
        """Get number of mailing lists within the mailing archive."""
        return len(self.lists)

    def __iter__(self):
        """Iterate over each mailing list within the mailing archive."""
        return iter(self.lists)

    def __getitem__(self, index):
        """Get specific mailing list at position `index` from the mailing archive."""
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
    ) -> "W3CArchive":
        """
        Create W3CArchive from a given URL.

        Parameters
        ----------
        name : Email archive name, such that multiple instances of `W3CArchive`
            can easily be distinguished.
        url_root : The invariant root URL that does not change no matter what
            part of the W3C archive we access.
        url_home : The 'home' space of the W3C archive. This is required as
            it contains the different sections which we obtain using `get_sections()`.
        select: Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        url_login : URL to the 'Log In' page.
        url_pref : URL to the 'Preferences'/settings page.
        login : Login credentials (username and password) that were used to set
            up AuthSession.
        session : requests.Session() object for the W3C Email archive website.
        instant_save : Boolean giving the choice to save a `W3CList` as
            soon as it is completely scraped or collect entire archive. The
            prior is recommended if a large number of mailing lists are
            scraped which can require a lot of memory and time.
        only_list_urls : Boolean giving the choice to collect only `W3CList`
            URLs or also their contents.
        """
        if session is None:
            session = get_auth_session(url_login, **login)
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
        url_mailing_lists: Union[List[str], List[W3CList]],
        select: Optional[dict] = None,
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        url_pref: str = "https://list.etsi.org/scripts/wa.exe?PREF",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        only_mlist_urls: bool = True,
        instant_save: Optional[bool] = True,
    ) -> "W3CArchive":
        """
        Create W3CArchive from a given list of 'W3CList'.

        Parameters
        ----------
        name : Email archive name, such that multiple instances of `W3CArchive`
            can easily be distinguished.
        url_root : The invariant root URL that does not change no matter what
            part of the W3C archive we access.
        url_mailing_lists : This argument can either be a list of `W3CList`
            objects or a list of string containing the URLs to the W3C
            Email lists of interest.
        url_login : URL to the 'Log In' page.
        url_pref : URL to the 'Preferences'/settings page.
        login : Login credentials (username and password) that were used to set
            up AuthSession.
        session : requests.Session() object for the W3C Email archive website.
        only_list_urls : Boolean giving the choice to collect only `W3CList`
            URLs or also their contents.
        instant_save : Boolean giving the choice to save a `W3CList` as
            soon as it is completely scraped or collect entire archive. The
            prior is recommended if a large number of mailing lists are
            scraped which can require a lot of memory and time.
        """
        if isinstance(url_mailing_lists[0], str) and only_mlist_urls is False:
            if session is None:
                session = get_auth_session(url_login, **login)
            lists = []
            for url in url_mailing_lists:
                mlist_name = url.split("A0=")[-1]
                mlist = W3CList.from_url(
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
    ) -> "W3CArchive":
        """
        This method is required if the files that contain the archive messages
        were directly exported from W3C.
        Each mailing list has its own subdirectory and is split over multiple
        files with an extension starting with LOG and ending with five digits.

        Parameters
        ----------
        name : Email archive name, such that multiple instances of `W3CArchive`
            can easily be distinguished.
        directorypath : Where the `W3CArchive` can be initialised.
        folderdsc : A description of the relevant folders
        filedsc : A description of the relevant files, e.g. *.LOG?????
        select : Selection criteria that can filter messages by:
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
            mlist = W3CList.from_listserv_files(
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
    ) -> "W3CArchive":
        """
        Parameters
        ----------
        name : Email archive name, such that multiple instances of `W3CArchive`
            can easily be distinguished.
        directorypath : Path to the folder in which `W3CArchive` is stored.
        filedsc : Optional filter that only reads files matching the description.
            By default all files with an mbox extension are read.
        """
        filepaths = get_paths_to_files_in_directory(directorypath, filedsc)
        lists = []
        for filepath in filepaths:
            name = filepath.split("/")[-1].split(".")[0]
            lists.append(W3CList.from_mbox(name, filepath))
        return cls(name, directorypath, lists)

    @staticmethod
    def get_lists_from_url(
        url_root: str,
        url_home: str,
        select: dict,
        session: Optional[str] = None,
        instant_save: bool = True,
        only_mlist_urls: bool = True,
    ) -> List[Union[W3CList, str]]:
        """
        Created dictionary of all lists in the archive.

        Parameters
        ----------
        url_root : The invariant root URL that does not change no matter what
            part of the W3C archive we access.
        url_home : The 'home' space of the W3C archive. This is required as
            it contains the different sections which we obtain using `get_sections()`.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        session : requests.Session() object for the W3C Email archive website.
        instant_save : Boolean giving the choice to save a `W3CList` as
            soon as it is completely scraped or collect entire archive. The
            prior is recommended if a large number of mailing lists are
            scraped which can require a lot of memory and time.
        only_list_urls : Boolean giving the choice to collect only `W3CList`
            URLs or also their contents.

        Returns
        -------
        archive_dict : the keys are the names of the lists and the value their url
        """
        archive = []
        # run through archive sections
        for url in list(W3CArchive.get_sections(url_root, url_home).keys()):
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
                    name = W3CList.get_name_from_url(mlist_url)
                    # check if mailing list contains messages in period
                    _period_urls = W3CList.get_all_periods_and_their_urls(
                        mlist_url
                    )[1]
                    # check if mailing list is public
                    if len(_period_urls) > 0:
                        loops = 0
                        for _period_url in _period_urls:
                            loops += 1
                            nr_msgs = len(
                                W3CList.get_messages_urls(
                                    name=name, url=_period_url
                                )
                            )
                            if nr_msgs > 0:
                                archive.append(mlist_url)
                                break
            else:
                # collect mailing-list contents
                for mlist_url in mlist_urls:
                    name = W3CList.get_name_from_url(mlist_url)
                    mlist = W3CList.from_url(
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

    def to_dict(self, include_body: bool = True) -> Dict[str, List[str]]:
        """
        Concatenates mailing list dictionaries created using
        `W3CList.to_dict()`.
        """
        return ArchiveIO.to_dict(self.lists, include_body)

    def to_pandas_dataframe(self, include_body: bool = True) -> pd.DataFrame:
        """
        Concatenates mailing list pandas.DataFrames created using
        `W3CList.to_pandas_dataframe()`.
        """
        return ArchiveIO.to_pandas_dataframe(self.lists, include_body)

    def to_mbox(self, dir_out: str):
        """
        Save Archive content to .mbox files
        """
        ArchiveIO.to_mbox(self.lists, dir_out)


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


def text_for_selector(soup: BeautifulSoup, selector: str):
    """
    Filter out header or body field from website and return them as utf-8 string.
    """
    results = soup.select(selector)
    if results:
        result = results[0].get_text(strip=True)
    else:
        result = ""
        logging.debug("No matching text for selector %s", selector)

    return str(result)


def parse_dfn_header(header_text):
    header_texts = str(header_text).split(":", 1)
    if len(header_texts) == 2:
        return header_texts[1]
    else:
        logging.debug("Split failed on %s", header_text)
        return ""
