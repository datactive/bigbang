import datetime
import email
import email.parser
import glob
import logging
import mailbox
import os
import re
import subprocess
import time
from urllib.parse import urlparse
from urllib.parse import urljoin
import warnings
from email.header import Header
from email.message import Message
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from config.config import CONFIG

project_directory = str(Path(os.path.abspath(__file__)).parent.parent)

logging.basicConfig(
    filename=project_directory + "/listserv.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


class ListservMessageWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class ListservListWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class ListservArchiveWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class ListservMessage:
    """
    Parameters
    ----------
    body
    subject
    fromname
    fromaddr
    toname
    toaddr
    date
    contenttype
    messageid

    Methods
    -------
    from_url
    get_header_from_html
    get_body_from_html
    get_header_from_listserv_file
    get_body_from_listserv_file
    get_name
    get_addr
    get_date
    remove_unwanted_header_content
    to_dict
    to_mbox

    Example
    -------
    msg = ListservMessage.from_url(
        list_name="3GPP_TSG_CT_WG6",
        url=url_message,
        fields="total",
    )
    """

    empty_header = {
        "subject": None,
        "fromname": None,
        "fromaddr": None,
        "toname": None,
        "toaddr": None,
        "date": "Mon, 11 Jan 1111 11:11:11",
        "contenttype": None,
    }

    def __init__(
        self,
        body: str,
        subject: str,
        fromname: str,
        fromaddr: str,
        toname: str,
        toaddr: str,
        date: str,
        contenttype: str,
        messageid: Optional[str] = None,
    ):
        self.body = body
        self.subject = subject
        self.fromname = fromname
        self.fromaddr = fromaddr
        self.toname = toname
        self.toaddr = toaddr
        self.date = date
        self.contenttype = contenttype

    @classmethod
    def from_url(
        cls,
        list_name: str,
        url: str,
        fields: str = "total",
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
    ) -> "ListservMessage":
        """
        Args:
        """
        if session is None:
            session = get_auth_session(url_login, **login)
        soup = get_website_content(url, session=session)
        if fields in ["header", "total"]:
            header = ListservMessage.get_header_from_html(soup)
        else:
            header = cls.empty_header
        if fields in ["body", "total"]:
            body = ListservMessage.get_body_from_html(list_name, url, soup)
        else:
            body = None
        return cls(body, **header)

    @classmethod
    def from_listserv_file(
        cls,
        list_name: str,
        file_path: str,
        header_start_line_nr: int,
        fields: str = "total",
    ) -> "ListservMessage":
        file = open(file_path, "r", errors="replace")
        fcontent = file.readlines()
        file.close()
        header_end_line_nr = cls.get_header_end_line_nr(
            fcontent, header_start_line_nr
        )
        if fields in ["header", "total"]:
            header = cls.get_header_from_listserv_file(
                fcontent, header_start_line_nr, header_end_line_nr
            )
        else:
            header = cls.empty_header
        if fields in ["body", "total"]:
            body = cls.get_body_from_listserv_file(
                fcontent, header_end_line_nr
            )
        else:
            body = None
        return cls(body, **header)

    @classmethod
    def get_header_end_line_nr(
        cls,
        content: List[str],
        header_start_line_nr: int,
    ) -> List[int]:
        """
        The header ends with the first empty line encountered.

        Args:
            content: The content of one LISTSERV-file.
        """
        for lnr, lcont in enumerate(content[header_start_line_nr:]):
            if len(lcont) <= 1:
                header_end_line_nr = header_start_line_nr + lnr
                break
        return header_end_line_nr

    @classmethod
    def get_header_from_listserv_file(
        cls,
        content: List[str],
        header_start_line_nr: int,
        header_end_line_nr: int,
    ) -> Dict[str, str]:
        """
        Args:
            content:
        """
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
        
        header = cls.format_header_content(header)
        header = cls.remove_unwanted_header_content(header)
        return header

    @classmethod
    def get_body_from_listserv_file(
        cls,
        content: List[str],
        header_end_line_nr: int,
    ) -> str:
        """"""
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

    @classmethod
    def get_header_from_html(cls, soup: BeautifulSoup) -> Dict[str, str]:
        """"""
        text = soup.find(
            "b",
            text=re.compile(r"^\bSubject\b"),
        ).parent.parent.parent.parent.text
        # collect important info from LISTSERV header
        header = {}
        for field in text.split("Parts/Attachments:")[0].splitlines():
            if len(field) == 0:
                continue
            field_name = field.split(":")[0].strip()
            field_body = field.replace(field_name + ":", "").strip()
            header[field_name.lower()] = field_body

        header = cls.format_header_content(header)
        header = cls.remove_unwanted_header_content(header)
        return header

    @staticmethod
    def get_body_from_html(
        list_name: str, url: str, soup: BeautifulSoup
    ) -> str:
        """"""
        try:
            url_root = ("/").join(url.split("/")[:-2])
            a_tags = soup.select(f'a[href*="A3="][href*="{list_name}"]')
            href_plain_text = [
                tag.get("href")
                for tag in a_tags
                if "Fplain" in tag.get("href")
            ][0]
            body_soup = get_website_content(
                urljoin(url_root, href_plain_text)
            )
            return body_soup.find("pre").text
        except Exception:
            logger.info(
                f"The message body of {url} which is part of the "
                f"list {list_name} could not be loaded."
            )
            return None

    @classmethod
    def format_header_content(cls, header: Dict[str, str]) -> Dict[str, str]:
        "Formats LISTSERV 16.5 header fields to mbox convention."
        # define formatting configuration
        formatting_header_conf = {
            "from": {
                "fromname": cls.get_name,
                "fromaddr": cls.get_addr,
            },
            "reply-to": {
                "toname": cls.get_name,
                "toaddr": cls.get_addr,
            },
            "date": {"date": cls.get_date},
            "content-type": {"contenttype": None},
        }
        # run through format settings
        for key_old, value in formatting_header_conf.items():
            # if header contains field
            if key_old in header.keys():
                for key_new, fct in formatting_header_conf[key_old].items():
                    if fct is None or header[key_old] is None:
                        header[key_new] = header[key_old]
                    else:
                        header[key_new] = fct(header[key_old])
            # if header misses field
            else:
                for key_new in formatting_header_conf[key_old].keys():
                    header[key_new] = cls.empty_header[key_new]
        return header

    @classmethod
    def remove_unwanted_header_content(
        cls, header: Dict[str, str]
    ) -> Dict[str, str]:
        for key in list(header.keys()):
            if key not in list(cls.empty_header.keys()):
                del header[key]
        return header

    @staticmethod
    def get_name(line: str) -> str:
        # get string in between < and >
        email_of_sender = re.findall(r"\<(.*)\>", line)
        if email_of_sender:
            # remove email_of_sender from line
            name = line.replace("<" + email_of_sender[0] + ">", "")
            # remove special characters
            name = re.sub(r"[^a-zA-Z0-9]+", " ", name)
        else:
            name = line
        return name.strip()

    @staticmethod
    def get_addr(line: str) -> Union[str, None]:
        # get string in between < and >
        email_addr = re.findall(r"\<(.*)\>", line)
        if email_addr:
            email_addr = email_addr[0].strip()
        else:
            email_addr = ListservMessage.empty_header["fromaddr"]
        return email_addr

    @staticmethod
    def get_date(line: str) -> str:
        line = (" ").join(line.split(" ")[:-1]).lstrip()
        # convert format to local version of date and time
        date_time_obj = datetime.datetime.strptime(
            line, "%a, %d %b %Y %H:%M:%S"
        )
        return date_time_obj.strftime("%c")
    
    @staticmethod
    def create_message_id(
        date: Union[str, None],
        from_address: Union[str, None],
    ) -> str:
        #if date is None:
        #    date = 'Wed Jan 11 11:11:11 1111'
        message_id = (".").join([date, from_address])
        # remove special characters
        message_id = re.sub(r"[^a-zA-Z0-9]+", "", message_id)
        return message_id

    def to_dict(self) -> Dict[str, str]:
        dic = {
            "Body": self.body,
            "Subject": self.subject,
            "FromName": self.fromname,
            "FromAddr": self.fromaddr,
            "ToName": self.toname,
            "ToAddr": self.toaddr,
            "Date": self.date,
            "ContentType": self.contenttype,
        }
        return dic

    def to_mbox(self, filepath: str, mode: str = "w"):
        """
        Safe mail list to .mbox files.
        """
        message_id = ListservMessage.create_message_id(
            self.date,
            self.fromaddr,
        )
        f = open(filepath, mode, encoding="utf-8")
        f.write("\n")
        # check that header was selected
        if self.subject is not None:
            f.write(f"From b'{self.fromaddr}' {self.date}\n")
            f.write(f"Content-Type: {self.contenttype}\n")
            f.write(f"MIME-Version: 1.0\n")
            f.write(f"In-Reply-To: {self.toname} <b'{self.toaddr}'>\n")
            f.write(f"From: {self.fromname} <b'{self.fromaddr}'>\n")
            f.write(f"Subject: b'{self.subject}\n")
            f.write(f"Message-ID: <{message_id}>'\n")
            f.write(f"Date: {self.date}'\n")
            f.write("\n")
        # check that body was selected
        if self.body is not None:
            f.write(self.body)
            f.write("\n")
        f.close()


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
        List of ListservMessage objects

    Methods
    -------
    from_url
    from_messages
    from_listserv_files
    from_listserv_directories
    get_messages_from_url
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
        msgs: List[ListservMessage],
    ):
        self.name = name
        self.source = source
        self.messages = msgs

    def __len__(self) -> int:
        return len(self.messages)

    def __iter__(self):
        return iter(self.messages)

    def __getitem__(self, index) -> ListservMessage:
        return self.messages[index]

    @classmethod
    def from_url(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = None,
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
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
        """
        if session is None:
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
        messages: List[Union[str, ListservMessage]],
        fields: str = "total",
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
    ) -> "ListservList":
        """
        Args:
            messages: Can either be a list of URLs to specific LISTSERV messages
                or a list of `ListservMessage` objects.
        """
        if not messages:
            # create empty ListservList for ListservArchive
            msgs = messages
        elif isinstance(messages[0], str):
            # create ListservList from message URLs
            if session is None:
                session = get_auth_session(url_login, **login)
            msgs = []
            for idx, url in enumerate(messages):
                msgs.append(
                    ListservMessage.from_url(
                        list_name=name,
                        url=url,
                        fields=fields,
                        session=session,
                    )
                )
        else:
            # create ListservList from list of ListservMessages
            msgs = messages
        return cls(name, url, msgs)

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
            for msg_nr in header_start_line_nrs:
                msgs.append(
                    ListservMessage.from_listserv_file(
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
    ) -> List[ListservMessage]:
        """
        Generator that yields all messages within a certain period
        (e.g. January 2021, Week 5).

        Args:
            name: Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'
            url: URL to the LISTSERV list.
            select: Selection criteria that can filter messages by:
                - content, i.e. header and/or body
                - period, i.e. written in a certain year, month, week-of-month
            session: AuthSession
        """
        if select is None:
            select = {"fields": "total"}
        msgs = []
        # run through periods
        for period_url in ListservList.get_period_urls(url, select):
            # run through messages within period
            for msg_url in ListservList.get_messages_urls(name, period_url):
                msgs.append(
                    ListservMessage.from_url(
                        name,
                        msg_url,
                        select["fields"],
                        session=session,
                    )
                )
                logger.info(f"Recorded the message {msg_url}.")
                # wait between loading messages, for politeness
                time.sleep(1)
        return msgs

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
    def get_all_periods_and_their_urls(url: str) -> Tuple[List[str], List[str]]:
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
                group of ListservMessage.
            urls: Corresponding URLs of each group of ListservMessage of which the
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

    @classmethod
    def get_messages_urls(cls, name: str, url: str) -> List[str]:
        """
        Args:
            name: Name of the `ListservList`
            url: URL to group of messages that are within the same period.

        Returns:
            List to URLs from which`ListservMessage` can be initialized.
        """
        url_root = ("/").join(url.split("/")[:-2])
        soup = get_website_content(url)
        a_tags = soup.select(f'a[href*="A2="][href*="{name}"]')
        if a_tags:
            a_tags = [
                urljoin(url_root, url.get("href"))
                for url in a_tags
            ]
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
        # run through messages
        for msg in self.messages:
            dic[f"ID{msg_nr}"] = msg.to_dict()
            msg_nr += 1
        return dic

    def to_dict(self) -> Dict[str, List[str]]:
        """
        Place all message into a dictionary of the form:
            dic = {
                "Subject": [messages[0], ... , messages[n]],
                .
                .
                .
                "ContentType": [messages[0], ... , messages[n]]
            }
        """
        # initialize dictionary
        dic = {}
        for key in list(self.messages[0].to_dict().keys()):
            dic[key] = []
        # run through messages
        for msg in self.messages:
            # run through message attributes
            for key, value in msg.to_dict().items():
                dic[key].append(value)
        return dic

    def to_pandas_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame.from_dict(self.to_dict())

    def to_mbox(self, dir_out: str, filename: Optional[str] = None):
        """
        Safe mail list to .mbox files.

        Args:
        """
        if filename is None:
            filepath = f"{dir_out}/{self.name}.mbox"
        else:
            filepath = f"{dir_out}/{filename}.mbox"
        logger.info(f"The list {self.name} is save at {filepath}.")
        first = True
        for msg in self.messages:
            if first:
                msg.to_mbox(filepath, mode="w")
                first = False
            else:
                msg.to_mbox(filepath, mode="a")


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

    def __init__(self, name: str, url: str, lists: List[ListservList]):
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
            url_login: URL to the login page
            login: login keys {"username": str, "password": str}
            session: if auth-session was already created externally
            instant_save: Boolean giving the choice to save a `ListservList` as
                soon as it is completely scraped or collect entire archive. The
                prior is recommended if a large number of mailing lists are
                scraped which can require a lot of memory and time.
            only_list_urls: Boolean giving the choice to collect only `ListservList`
                URLs or also their contents.
        """
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
        url_mailing_lists: Union[List[str], List[ListservList]],
        select: Optional[dict] = None,
        url_login: str = "https://list.etsi.org/scripts/wa.exe?LOGON",
        login: Optional[Dict[str, str]] = {"username": None, "password": None},
        session: Optional[str] = None,
        only_mlist_urls: bool = True,
    ) -> "ListservArchive":
        """
        Create ListservArchive from a given list of 'ListservList'.

        Args:
            name:
            url_root:
            url_mailing_lists:

        """
        if isinstance(url_mailing_lists[0], str) and only_mlist_urls is False:
            if session is None:
                session = get_auth_session(url_login, **login)
            lists = []
            for idx, url in enumerate(url_mailing_lists):
                lists.append(
                    ListservList.from_url(
                        name=idx,
                        url=url,
                        select=select,
                        session=session,
                    )
                )
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
    ) -> "ListservList":
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
                [
                    archive.append(mlist_url)
                    for mlist_url in mlist_urls
                    if len(ListservList.get_all_periods_and_their_urls(mlist_url)[1]) > 0
                ]

            else:
                # collect mailing-list contents
                for mlist_url in mlist_urls:
                    key = mlist_url.split("A0=")[-1]
                    mlist = ListservList.from_url(
                        name=key,
                        url=mlist_url,
                        select=select,
                        session=session,
                    )
                    if len(mlist) != 0:
                        if instant_save:
                            mlist.to_mbox(dir_out=CONFIG.mail_path)
                            archive.append(mlist.name)
                        else:
                            logger.info(f"Recorded the list {mlist.name}.")
                            archive.append(mlist)
        return archive

    def get_sections(url_root: str, url_home: str) -> int:
        """
        Get different sections of archive. On the website they look like:
        [3GPP] [3GPP–AT1] [AT2–CONS] [CONS–EHEA] [EHEA–ERM_] ...

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
            archive_sections_dict[re.sub(r'p=[0-9]+', 'p=1', key)] = 'FIRST'
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

    def to_dict(self) -> Dict[str, List[str]]:
        """
        Place all message in all lists into a dictionary of the form:
            dic = {
                "Subject": [messages[0], ... , messages[n]],
                .
                .
                .
                "ListName": [messages[0], ... , messages[n]]
            }
        """
        # initialize dictionary
        dic = {}
        for key in list(self.lists[0].messages[0].to_dict().keys()):
            dic[key] = []
        dic["ListName"] = []
        # run through lists
        for mlist in self.lists:
            # run through messages
            for msg in mlist.messages:
                # run through message attributes
                for key, value in msg.to_dict().items():
                    dic[key].append(value)
                dic["ListName"].append(mlist.name)
        return dic

    def to_pandas_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame.from_dict(self.to_dict())

    def to_mbox(self, dir_out: str):
        """
        Save Archive content to .mbox files
        """
        for llist in self.lists:
            llist.to_mbox(dir_out)


def get_auth_session(
    url_login: str, username: str, password: str
) -> requests.Session:
    """ Create AuthSession """
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
    file_auth: str = project_directory + "/config/authentication.yaml",
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
    """ Safe login key to yaml """
    file = open(file_auth, "w")
    file.write(f"username: '{username}'\n")
    file.write(f"password: '{password}'")
    file.close()


def get_website_content(
    url: str,
    session: Optional[requests.Session] = None,
) -> BeautifulSoup:
    """ Get HTML code from website """
    # TODO: include option to change BeautifulSoup args
    if session is None:
        sauce = requests.get(url)
        assert sauce.status_code == 200
        soup = BeautifulSoup(sauce.content, "html.parser")
    else:
        sauce = session.get(url)
        soup = BeautifulSoup(sauce.text, "html.parser")
    return soup


def get_paths_to_files_in_directory(
    directory: str, file_dsc: str = "*"
) -> List[str]:
    """ Get paths of all files matching file_dsc in directory """
    template = f"{directory}{file_dsc}"
    file_paths = glob.glob(template)
    return file_paths


def get_paths_to_dirs_in_directory(
    directory: str, folder_dsc: str = "*"
) -> List[str]:
    """ Get paths of all directories matching file_dsc in directory """
    template = f"{directory}{folder_dsc}"
    dir_paths = glob.glob(template)
    # normalize directory paths
    dir_paths = [dir_path + "/" for dir_path in dir_paths]
    return dir_paths
