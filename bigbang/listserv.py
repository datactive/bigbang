import datetime
import email
import email.parser
import glob
import mailbox
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
from email.header import Header
from email.message import Message
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup


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
    """

    empty_header = {
        "subject": None,
        "fromname": None,
        "fromaddr": None,
        "toname": None,
        "toaddr": None,
        "date": None,
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
    ) -> "ListservMessage":
        """
        Args:
        """
        # TODO implement field selection, e.g. return only header, body, etc.
        soup = get_website_content(url)
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
        file = open(file_path, "r")
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
        url_root = ("/").join(url.split("/")[:-2])
        a_tags = soup.select(f'a[href*="A3="][href*="{list_name}"]')
        href_plain_text = [
            tag.get("href") for tag in a_tags if "Fplain" in tag.get("href")
        ][0]
        body_soup = get_website_content(
            urllib.parse.urljoin(url_root, href_plain_text)
        )
        return body_soup.find("pre").text

    @classmethod
    def format_header_content(cls, header: Dict[str, str]) -> Dict[str, str]:
        header["fromname"] = cls.get_name(header["from"]).strip()
        header["fromaddr"] = cls.get_addr(header["from"])
        header["toname"] = cls.get_name(header["reply-to"]).strip()
        header["toaddr"] = cls.get_addr(header["reply-to"])
        header["date"] = cls.get_date(header["date"])
        header["contenttype"] = header["content-type"]
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
        return name

    @staticmethod
    def get_addr(line: str) -> str:
        # get string in between < and >
        email_of_sender = re.findall(r"\<(.*)\>", line)
        if email_of_sender:
            email_of_sender = email_of_sender[0]
        else:
            email_of_sender = None
        return email_of_sender

    @staticmethod
    def get_date(line: str) -> str:
        line = (" ").join(line.split(" ")[:-1]).lstrip()
        # convert format to local version of date and time
        date_time_obj = datetime.datetime.strptime(
            line, "%a, %d %b %Y %H:%M:%S"
        )
        return date_time_obj.strftime("%c")

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
        select: dict,
    ) -> "ListservList":
        """
        Args:
            name: Name of the list of messages, e.g. '3GPP_TSG_SA_WG2_UPCON'
            url: URL to the LISTSERV list.
            select: Selection criteria that can filter messages by:
                - content, i.e. header and/or body
                - period, i.e. written in a certain year, month, week-of-month
        """
        if "fields" not in list(select.keys()):
            select["fields"] = "total"
        msgs = cls.get_messages_from_url(name, url, select)
        return cls.from_messages(name, url, msgs)

    @classmethod
    def from_messages(
        cls,
        name: str,
        url: str,
        messages: List[Union[str, ListservMessage]],
        fields: str = "total",
    ) -> "ListservList":
        """
        Args:
            messages: Can either be a list of URLs to specific LISTSERV messages
                or a list of `ListservMessage` objects.
        """
        if not messages:
            msgs = messages
        elif isinstance(messages[0], str):
            msgs = []
            for idx, url in enumerate(messages):
                msgs.append(
                    ListservMessage.from_url(
                        list_name=name,
                        url=url,
                        fields=fields,
                    )
                )
        else:
            msgs = messages
        return cls(name, url, msgs)

    @classmethod
    def from_listserv_directories(
        cls,
        name: str,
        directorypaths: List[str],
        filedsc: str,
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
                get_all_file_from_directory(directorypath, filedsc)
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
            print(filepath)
            # TODO: implement selection filter
            file = open(filepath, "r")
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
    ) -> List[ListservMessage]:
        """
        Generator that yields all messages within a certain period
        (e.g. January 2021, Week 5).
        """
        if select is None:
            select = {"fields": "total"}

        msgs = []
        # run through periods
        for period_url in ListservList.get_period_urls(url, select):
            # run through messages within period
            for msg_url in ListservList.get_messages_urls(name, period_url):
                msgs.append(
                    ListservMessage.from_url(name, msg_url, select["fields"])
                )
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
        url_root = ("/").join(url.split("/")[:-2])
        soup = get_website_content(url)
        # create dictionary with key indicating period and values the url
        periods = [list_tag.find("a").text for list_tag in soup.find_all("li")]
        urls_of_periods = [
            urllib.parse.urljoin(url_root, list_tag.find("a").get("href"))
            for list_tag in soup.find_all("li")
        ]

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
                urllib.parse.urljoin(url_root, url.get("href"))
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
        select: dict,
    ) -> "ListservArchive":
        """
        Create ListservArchive from a given URL.

        Args:
            name:
            url_root:
            url_home:
            select:
        """
        lists = cls.get_lists_from_url(url_root, url_home, select)
        return cls.from_mailing_lists(name, url_root, lists, select)

    @classmethod
    def from_mailing_lists(
        cls,
        name: str,
        url_root: str,
        url_mailing_lists: Union[List[str], List[ListservList]],
        select: dict,
    ) -> "ListservArchive":
        """
        Create ListservArchive from a given list of 'ListservList'.

        Args:
            name:
            url_root:
            url_mailing_lists:

        """
        if isinstance(url_mailing_lists[0], str):
            lists = []
            for idx, url in enumerate(url_mailing_lists):
                lists.append(
                    ListservList.from_url(name=idx, url=url, select=select)
                )
        else:
            lists = url_mailing_lists
        return cls(name, url_root, lists)

    @staticmethod
    def get_lists_from_url(
        url_root: str,
        url_home: str,
        select: dict,
    ) -> List[ListservList]:
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
        )[:1]:
            soup = get_website_content(url)
            a_tags_in_section = soup.select(
                'a[href*="A0="][onmouseover*="showDesc"][onmouseout*="hideDesc"]',
            )

            # run through archive lists in section
            for a_tag in a_tags_in_section:
                value = urllib.parse.urljoin(url_root, a_tag.get("href"))
                key = value.split("A0=")[-1]
                mlist = ListservList.from_url(
                    name=key, url=value, select=select
                )
                if len(mlist) != 0:
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
                key = urllib.parse.urljoin(url_root, sec.get("href"))
                value = sec.text
                if value in ["Next", "Previous"]:
                    continue
                archive_sections_dict[key] = value
            # TODO check that p=1 is included
        else:
            archive_sections_dict[url_home] = "Home"
        return archive_sections_dict

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
        for llist in self.lists[1:2]:
            llist.to_mbox(dir_out)


def get_website_content(
    url: str,
) -> BeautifulSoup:
    """"""
    resp = urllib.request.urlopen(url)
    assert resp.getcode() == 200
    # TODO: include option to change BeautifulSoup args
    return BeautifulSoup(resp.read(), features="lxml")


def get_all_file_from_directory(directory: str, file_dsc: str) -> List[str]:
    """ Get paths of all files matching file_dsc in directory """
    template = f"{directory}{file_dsc}"
    file_paths = glob.glob(template)
    return file_paths


if __name__ == "__main__":
    mlist = ListservList.from_listserv_directories(
        "3GPP_TSG_SA_WG2_UPCON",
        directorypaths=["../archives/3GPP_TSG_SA_WG2_UPCON/"],
        filedsc="*.LOG?????"
        # select={
        #    "years": 2021,
        #    "months": "January",
        #    "weeks": 1,
        #    "fields": "header",
        # },
    )
    print(f"Lenght of mlist = {len(mlist)}")
    print(mlist.messages[0].subject)
    # test = arch.to_mbox("/home/christovis/02_AGE/datactive/")
