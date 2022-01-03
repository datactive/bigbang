from tqdm import tqdm
import time
import logging
import os
import email
from abc import ABC, abstractmethod
import mailbox
from mailbox import mboxMessage
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from config.config import CONFIG
from bigbang.utils import get_paths_to_files_in_directory
from bigbang.bigbang_io import MessageIO, ListIO, ArchiveIO
from bigbang.ingress.utils import get_website_content

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
logging.basicConfig(
    filename=directory_project + "/abstract.scraping.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


class AbstractMessageParserWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class AbstractListWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class AbstractArchiveWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class AbstractMessageParser(ABC):
    """
    This class handles the creation of an mailbox.mboxMessage object
    (using the from_*() methods) and its storage in various other file formats
    (using the to_*() methods) that can be saved on the local memory.
    """

    def __init__(
        self,
        website=False,
        url_login: Optional[str] = None,
        url_pref: Optional[str] = None,
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[requests.Session] = None,
    ):
        if website:
            if (session is None) and (url_login is not None):
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
        # convert to `EmailMessage` to `mboxMessage`
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
        list_name : The name of the mailing list.
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

    @abstractmethod
    def _get_header_from_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        pass

    @abstractmethod
    def _get_body_from_html(
        self, list_name: str, url: str, soup: BeautifulSoup
    ) -> Union[str, None]:
        pass

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


class AbstractList(ABC):
    """
    This class handles the scraping of a all public Emails contained in a single
    mailing list. To be more precise, each contributor to a mailing list sends
    their message to an Email address that has the following structure:
    <mailing_list_name>@<mailing_archive_name>.
    Thus, this class contains all Emails send to a specific <mailing_list_name>
    (the Email localpart).

    Parameters
    ----------
    name : The of whom the list (e.g. 3GPP_COMMON_IMS_XFER, IEEESCO-DIFUSION, ...)
    source : Contains the information of the location of the mailing list.
        It can be either an URL where the list or a path to the file(s).
    msgs : List of mboxMessage objects

    Methods
    -------
    from_url()
    from_messages()
    from_mbox()
    get_message_urls()
    get_messages_from_url()
    get_index_of_elements_in_selection()
    get_name_from_url()
    to_dict()
    to_pandas_dataframe()
    to_mbox()
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

    def __getitem__(self, index) -> mboxMessage:
        """Get specific message at position `index` within the mailing list."""
        return self.messages[index]

    @classmethod
    @abstractmethod
    def from_url(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = {"fields": "total"},
        url_login: Optional[str] = None,
        url_pref: Optional[str] = None,
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[requests.Session] = None,
    ) -> "AbstractList":
        """
        Parameters
        ----------
        name : Name of the mailing list.
        url : URL to the mailing list.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        url_login : URL to the 'Log In' page
        url_pref : URL to the 'Preferences'/settings page
        login : Login credentials (username and password) that were used to set
            up AuthSession.
        session : requests.Session() object for the Email archive website.
        """
        pass

    @classmethod
    @abstractmethod
    def from_messages(
        cls,
        name: str,
        url: str,
        messages: List[Union[str, mboxMessage]],
        fields: str = "total",
        url_login: str = None,
        url_pref: str = None,
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
    ) -> "AbstractList":
        """
        Parameters
        ----------
        name : Name of the list of messages, e.g. 'public-bigdata'
        url : URL to the Email list.
        messages : Can either be a list of URLs to specific messages
            or a list of `mboxMessage` objects.
        url_login : URL to the 'Log In' page.
        url_pref : URL to the 'Preferences'/settings page.
        login : Login credentials (username and password) that were used to set
            up AuthSession. You can create your own for the archive.
        session : requests.Session() object for the Email archive website.
        """
        pass

    @classmethod
    @abstractmethod
    def from_mbox(cls, name: str, filepath: str) -> "AbstractList":
        """
        Parameters
        ----------
        name : Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'.
        filepath : Path to file in which mailing list is stored.
        """
        pass

    @classmethod
    @abstractmethod
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
        url : URL to the mailing list.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year and month

        Returns
        -------
        List of all selected URLs of the messages in the mailing list.
        """
        pass

    @staticmethod
    def get_messages_from_urls(
        name: str,
        msg_urls: list,
        msg_parser,
        fields: Optional[str] = "total",
    ) -> List[mboxMessage]:
        """
        Generator that returns all messages within a certain period
        (e.g. January 2021, Week 5).

        Parameters
        ----------
        name : Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'
        url : URL to the mailing list.
        fields : Content, i.e. header and/or body
        """
        # get all message contents
        msgs = []
        for msg_url in tqdm(msg_urls, ascii=True, desc=name):
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
            # wait between loading messages, for politeness
            time.sleep(1)
        return msgs

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

    @abstractmethod
    def get_name_from_url(url: str) -> str:
        pass

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


class AbstractArchive(ABC):
    """
    This class handles the scraping of a all public Emails contained in a mailing
    archive. To be more precise, each contributor to a mailing archive sends
    their message to an Email address that has the following structure:
    <mailing_list_name>@<mailing_archive_name>.
    Thus, this class contains all Emails send to <mailing_archive_name>
    (the Email domain name). These Emails are contained in a list of
    `AbstractList` types, such that it is known to which <mailing_list_name>
    (the Email localpart) was send.

    Parameters
    ----------
    name : The archive name (e.g. 3GPP, IEEE, W3C)
    url : The URL where the archive lives
    lists : A list containing the mailing lists as `AbstractList` types

    Methods
    -------
    from_url()
    from_mailing_lists()
    from_mbox()
    get_lists_from_url()
    to_dict()
    to_pandas_dataframe()
    to_mbox()
    """

    def __init__(
        self, name: str, url: str, lists: List[Union[AbstractList, str]]
    ):
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
    @abstractmethod
    def from_url(
        cls,
        name: str,
        url_root: str,
        url_home: Optional[str] = None,
        select: Optional[dict] = None,
        url_login: Optional[str] = None,
        url_pref: Optional[str] = None,
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        instant_save: bool = True,
        only_mlist_urls: bool = True,
    ) -> "AbstractArchive":
        """
        Create a mail archive from a given URL.
        Parameters
        ----------
        name : Email archive name, such that multiple instances of `AbstractArchive`
            can easily be distinguished.
        url_root : The invariant root URL that does not change no matter what
            part of the archive we access.
        url_home : The 'home' space of the archive. This is required as
            it contains the different sections which we obtain using `get_sections()`.
        select: Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        url_login : URL to the 'Log In' page.
        url_pref : URL to the 'Preferences'/settings page.
        login : Login credentials (username and password) that were used to set
            up AuthSession.
        session : requests.Session() object for the Email archive website.
        instant_save : Boolean giving the choice to save a `AbstractList` as
            soon as it is completely scraped or collect entire archive. The
            prior is recommended if a large number of mailing lists are
            scraped which can require a lot of memory and time.
        only_list_urls : Boolean giving the choice to collect only `AbstractList`
            URLs or also their contents.
        """
        pass

    @classmethod
    @abstractmethod
    def from_mailing_lists(
        cls,
        name: str,
        url_root: str,
        url_mailing_lists: Union[List[str], List[AbstractList]],
        select: Optional[dict] = None,
        url_login: Optional[str] = None,
        url_pref: Optional[str] = None,
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        only_mlist_urls: bool = True,
        instant_save: Optional[bool] = True,
    ) -> "AbstractArchive":
        """
        Create mailing archive from a given list of 'AbstractList` instances or URLs
        pointing to mailing lists.

        Parameters
        ----------
        name : Email archive name, such that multiple instances of `AbstractArchive`
            can easily be distinguished.
        url_root : The invariant root URL that does not change no matter what
            part of the archive we access.
        url_mailing_lists : This argument can either be a list of `AbstractList`
            objects or a list of string containing the URLs to the mailing
            list of interest.
        url_login : URL to the 'Log In' page.
        url_pref : URL to the 'Preferences'/settings page.
        login : Login credentials (username and password) that were used to set
            up AuthSession.
        session : requests.Session() object for the archive website.
        only_list_urls : Boolean giving the choice to collect only mailing list
            URLs or also their contents.
        instant_save : Boolean giving the choice to save a `AbstractList` as
            soon as it is completely scraped or collect entire archive. The
            prior is recommended if a large number of mailing lists are
            scraped which can require a lot of memory and time.
        """
        pass

    @classmethod
    @abstractmethod
    def from_mbox(
        cls,
        name: str,
        directorypath: str,
        filedsc: str = "*.mbox",
    ) -> "AbstractArchive":
        """
        Parameters
        ----------
        name : Email archive name, such that multiple instances of `AbstractArchive`
            can easily be distinguished.
        directorypath : Path to the folder in which `AbstractArchive` is stored.
        filedsc : Optional filter that only reads files matching the description.
            By default all files with an mbox extension are read.
        """
        pass

    @classmethod
    @abstractmethod
    def get_lists_from_url(
        url_root: str,
        url_home: str,
        select: dict,
        session: Optional[str] = None,
        instant_save: bool = True,
        only_mlist_urls: bool = True,
    ) -> List[Union[AbstractList, str]]:
        """
        Created dictionary of all lists in the archive.

        Parameters
        ----------
        url_root : The invariant root URL that does not change no matter what
            part of the archive we access.
        url_home : The 'home' space of the archive. This is required as
            it contains the different sections which we obtain using `get_sections()`.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        session : requests.Session() object for the archive website.
        instant_save : Boolean giving the choice to save a `AbstractList` as
            soon as it is completely scraped or collect entire archive. The
            prior is recommended if a large number of mailing lists are
            scraped which can require a lot of memory and time.
        only_list_urls : Boolean giving the choice to collect only `AbstractList`
            URLs or also their contents.

        Returns
        -------
        archive_dict : the keys are the names of the lists and the value their url
        """
        pass

    def to_dict(self, include_body: bool = True) -> Dict[str, List[str]]:
        """
        Concatenates mailing list dictionaries created using
        `AbstractList.to_dict()`.
        """
        return ArchiveIO.to_dict(self.lists, include_body)

    def to_pandas_dataframe(self, include_body: bool = True) -> pd.DataFrame:
        """
        Concatenates mailing list pandas.DataFrames created using
        `AbstractList.to_pandas_dataframe()`.
        """
        return ArchiveIO.to_pandas_dataframe(self.lists, include_body)

    def to_mbox(self, dir_out: str):
        """
        Save Archive content to .mbox files
        """
        ArchiveIO.to_mbox(self.lists, dir_out)


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
