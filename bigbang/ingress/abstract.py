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

from bigbang.config import CONFIG
from bigbang.utils import get_paths_to_files_in_directory
import bigbang.bigbang_io as bio
from bigbang.data_types import Message, MailList
from bigbang.ingress.utils import (
    get_website_content,
    get_auth_session,
    set_website_preference_for_header,
)

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
    """Base class for AbstractMessageParser class specific exceptions"""

    pass


class AbstractMailListWarning(BaseException):
    """Base class for AbstractMailList class specific exceptions"""

    pass


class AbstractMailListDomainWarning(BaseException):
    """Base class for AbstractMailListDomain class specific exceptions"""

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
        """
        If message is read from an URL (instead of a locally stored file),
        it might be necessary to create an authentication session or have the
        required SSL certificates. Therefore in the initialisation of this class,
        the necessary method is declared.
        """
        if website:
            if (session is None) and (url_login is not None):
                session = get_auth_session(url_login, **login)
                session = set_website_preference_for_header(url_pref, session)
            self.session = session

    def create_email_message(
        self,
        archived_at: str,
        body: str,
        attachments: Optional[List] = None,
        **header,
    ) -> Message:
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
            if "from" == key:
                value = value.replace(" at ", "@")

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

        if (msg["Message-ID"] is None) and isinstance(archived_at, str):
            msg["Message-ID"] = archived_at.split("/")[-1]

        # convert to `EmailMessage` to `mboxMessage`
        mbox_msg = mboxMessage(msg)
        mbox_msg.add_header("Archived-At", "<" + str(archived_at) + ">")

        if attachments is not None:
            for idx, attachment in enumerate(attachments):
                mbox_msg.add_header(
                    "Attachment-%d" % idx,
                    attachment.text,
                    filename=attachment.filename,
                )
        return mbox_msg

    def from_url(
        self,
        list_name: str,
        url: str,
        fields: str = "total",
    ) -> Message:
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
            header = self.empty_header
            body = "RequestException"
            attachments = "RequestException"

        else:
            if fields in ["header", "total"]:
                header = self._get_header_from_html(soup)
            else:
                header = self.empty_header
            if fields in ["body", "total"]:
                body = self._get_body_from_html(list_name, url, soup)
                if "lists.w3.org" in url:
                    attachments = None
                elif "listserv." in url:
                    attachments = self._get_attachments_from_html(list_name, url, soup)
            else:
                body = None
                attachments = None

        return self.create_email_message(url, body, attachments, **header)

    @staticmethod
    def to_dict(msg: Message) -> Dict[str, List[str]]:
        """Convert mboxMessage to a Dictionary"""
        return bio.email_to_dict(msg)

    @staticmethod
    def to_pandas_dataframe(msg: Message) -> pd.DataFrame:
        """Convert mboxMessage to a pandas.DataFrame"""
        return bio.email_to_pandas_dataframe(msg)

    @staticmethod
    def to_mbox(msg: Message, filepath: str):
        """
        Parameters
        ----------
        msg : The Email.
        filepath : Path to file in which the Email will be stored.
        """
        return bio.email_to_mbox(msg, filepath)


class AbstractMailList(ABC):
    """
    This class handles the scraping of a all public Emails contained in a single
    mailing list. To be more precise, each contributor to a mailing list sends
    their message to an Email address that has the following structure:
    <mailing_list_name>@<mail_list_domain_name>.
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
        msgs: MailList,
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

    def __getitem__(self, index) -> Message:
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
    ) -> "AbstractMailList":
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
        session : requests.Session() object for the Email list domain website.
        """
        pass

    @classmethod
    @abstractmethod
    def from_messages(
        cls,
        name: str,
        url: str,
        messages: Union[List[str], MailList],
        fields: str = "total",
        url_login: str = None,
        url_pref: str = None,
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
    ) -> "AbstractMailList":
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
            up AuthSession.
        session : requests.Session() object for the Email list domain website.
        """
        pass

    @classmethod
    @abstractmethod
    def from_mbox(cls, name: str, filepath: str) -> "AbstractMailList":
        """
        Parameters
        ----------
        name : Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'.
        filepath : Path to file in which mailing list is stored.
        """
        pass

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
    ) -> MailList:
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
        return bio.mlist_to_dict(self.messages, include_body)

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
        return bio.mlist_to_pandas_dataframe(self.messages, include_body)

    def to_mbox(self, dir_out: str, filename: Optional[str] = None):
        """Safe mailing list to .mbox files."""
        if filename is None:
            bio.mlist_to_mbox(self.messages, dir_out, self.name)
        else:
            bio.mlist_to_mbox(self.messages, dir_out, filename)


class AbstractMailListDomain(ABC):
    """
    This class handles the scraping of a all public Emails contained in a mail
    list domain. To be more precise, each contributor to a mailing archive sends
    their message to an Email address that has the following structure:
    <mailing_list_name>@<mail_list_domain_name>.
    Thus, this class contains all Emails send to <mail_list_domain_name>
    (the Email domain name). These Emails are contained in a list of
    `AbstractMailList` types, such that it is known to which <mailing_list_name>
    (the Email localpart) was send.

    Parameters
    ----------
    name : The mail list domain name (e.g. 3GPP, IEEE, W3C)
    url : The URL where the archive lives
    lists : A list containing the mailing lists as `AbstractMailList` types

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

    def __init__(self, name: str, url: str, lists: List[Union[AbstractMailList, str]]):
        self.name = name
        self.url = url
        self.lists = lists

    def __len__(self):
        """Get number of mailing lists within the mail list domain."""
        return len(self.lists)

    def __iter__(self):
        """Iterate over each mailing list within the mail list domain."""
        return iter(self.lists)

    def __getitem__(self, index):
        """Get specific mailing list at position `index` from the mail list domain."""
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
    ) -> "AbstractMailListDomain":
        """
        Create a mail list domain from a given URL.
        Parameters
        ----------
        name : Email list domain name, such that multiple instances of
            `AbstractMailListDomain` can easily be distinguished.
        url_root : The invariant root URL that does not change no matter what
            part of the mail list domain we access.
        url_home : The 'home' space of the mail list domain. This is required as
            it contains the different sections which we obtain using `get_sections()`.
        select: Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        url_login : URL to the 'Log In' page.
        url_pref : URL to the 'Preferences'/settings page.
        login : Login credentials (username and password) that were used to set
            up AuthSession.
        session : requests.Session() object for the mail list domain website.
        instant_save : Boolean giving the choice to save a `AbstractMailList` as
            soon as it is completely scraped or collect entire mail list domain. The
            prior is recommended if a large number of mailing lists are
            scraped which can require a lot of memory and time.
        only_list_urls : Boolean giving the choice to collect only `AbstractMailList`
            URLs or also their contents.
        """
        pass

    @classmethod
    @abstractmethod
    def from_mailing_lists(
        cls,
        name: str,
        url_root: str,
        url_mailing_lists: Union[List[str], List[AbstractMailList]],
        select: Optional[dict] = None,
        url_login: Optional[str] = None,
        url_pref: Optional[str] = None,
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        only_mlist_urls: bool = True,
        instant_save: Optional[bool] = True,
    ) -> "AbstractMailListDomain":
        """
        Create mailing mail list domain from a given list of 'AbstractMailList` instances or URLs
        pointing to mailing lists.

        Parameters
        ----------
        name : mail list domain name, such that multiple instances of
            `AbstractMailListDomain` can easily be distinguished.
        url_root : The invariant root URL that does not change no matter what
            part of the mail list domain we access.
        url_mailing_lists : This argument can either be a list of `AbstractMailList`
            objects or a list of string containing the URLs to the mailing
            list of interest.
        url_login : URL to the 'Log In' page.
        url_pref : URL to the 'Preferences'/settings page.
        login : Login credentials (username and password) that were used to set
            up AuthSession.
        session : requests.Session() object for the mail list domain website.
        only_list_urls : Boolean giving the choice to collect only mailing list
            URLs or also their contents.
        instant_save : Boolean giving the choice to save a `AbstractMailList` as
            soon as it is completely scraped or collect entire mail list domain. The
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
    ) -> "AbstractMailListDomain":
        """
        Parameters
        ----------
        name : mail list domain name, such that multiple instances of
            `AbstractMailListDomain` can easily be distinguished.
        directorypath : Path to the folder in which `AbstractMailListDomain` is stored.
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
    ) -> List[Union[AbstractMailList, str]]:
        """
        Created dictionary of all lists in the mail list domain.

        Parameters
        ----------
        url_root : The invariant root URL that does not change no matter what
            part of the mail list domain we access.
        url_home : The 'home' space of the mail list domain. This is required as
            it contains the different sections which we obtain using `get_sections()`.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year, month, week-of-month
        session : requests.Session() object for the mail list domain website.
        instant_save : Boolean giving the choice to save a `AbstractMailList` as
            soon as it is completely scraped or collect entire mail list domain. The
            prior is recommended if a large number of mailing lists are
            scraped which can require a lot of memory and time.
        only_list_urls : Boolean giving the choice to collect only `AbstractMailList`
            URLs or also their contents.

        Returns
        -------
        archive_dict : the keys are the names of the lists and the value their url
        """
        pass

    def to_dict(self, include_body: bool = True) -> Dict[str, List[str]]:
        """
        Concatenates mailing list dictionaries created using
        `AbstractMailList.to_dict()`.
        """
        return bio.mlistdom_to_dict(self.lists, include_body)

    def to_pandas_dataframe(self, include_body: bool = True) -> pd.DataFrame:
        """
        Concatenates mailing list pandas.DataFrames created using
        `AbstractMailList.to_pandas_dataframe()`.
        """
        return bio.mlistdom_to_pandas_dataframe(self.lists, include_body)

    def to_mbox(self, dir_out: str):
        """
        Save mail list domain content to .mbox files
        """
        bio.mlistdom_to_mbox(self.lists, dir_out + "/" + self.name)
