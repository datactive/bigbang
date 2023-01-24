from tqdm import tqdm
import email
import logging
import os
import re
import subprocess
import time
import warnings
import tempfile
import gzip
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
)
from bigbang.ingress.utils import (
    get_website_content,
    set_website_preference_for_header,
    get_auth_session,
)
from bigbang.utils import (
    get_paths_to_files_in_directory,
    get_paths_to_dirs_in_directory,
)

dir_temp = tempfile.gettempdir()
filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent.parent)
logging.basicConfig(
    filename=directory_project + "/icann.scraping.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


class PipermailMessageParserWarning(BaseException):
    """Base class for PipermailMessageParser class specific exceptions"""

    pass


class PipermailMailListWarning(BaseException):
    """Base class for PipermailMailList class specific exceptions"""

    pass


class PipermailMailListDomainWarning(BaseException):
    """Base class for PipermailMailListDomain class specific exceptions"""

    pass


class PipermailMessageParser(AbstractMessageParser, email.parser.Parser):
    """
    This class handles the creation of an `mailbox.mboxMessage` object
    (using the from_*() methods) and its storage in various other file formats
    (using the to_*() methods) that can be saved on the local memory.

    Parameters
    ----------
    url_pref : URL to the 'Preferences'/settings page.


    Example
    -------
    To create a Email message parser object, use the following syntax:
    >>> msg_parser = PipermailMessageParser()

    To obtain the Email message content and return it as `mboxMessage` object,
    you need to do the following:
    >>> msg = msg_parser.from_url(
    >>>     list_name="public-2018-permissions-ws",
    >>>     url="https://lists.w3.org/Archives/Public/public-2018-permissions-ws/2019May/0000.html",
    >>>     fields="total",
    >>> )
    """

    empty_header = {}

    def from_pipermail_file(
        self,
        list_name: str,
        fcontent: str,
        header_end_line_nr: int,
        fields: str = "total",
    ) -> mboxMessage:
        """ """
        header_start_line_nr = self.find_start_of_header(fcontent, header_end_line_nr)

        if header_start_line_nr is None:
            logger.info(
                "The start of header in {list_name}"
                + " {header_end_line_nr} couldnt be found."
            )
            print(
                f"The start of header in {list_name}"
                + f"{header_end_line_nr} couldnt be found."
            )
            archived_at = None
            body = None
            header = {}

        else:
            if fields in ["header", "total"]:
                header = self._get_header_from_pipermail_file(
                    fcontent, header_start_line_nr, header_end_line_nr
                )
            else:
                header = self.empty_header
            if fields in ["body", "total"]:
                body = self._get_body_from_pipermail_file(fcontent, header_end_line_nr)
            else:
                body = None
            archived_at = f"{list_name}_line_nr_{header_start_line_nr}"

        return self.create_email_message(archived_at, body, **header)

    def _get_header_from_pipermail_file(
        self,
        fcontent: List[str],
        header_start_line_nr: int,
        header_end_line_nr: int,
    ) -> Dict[str, str]:
        """
        Lexer for the message header.

        Parameters
        ----------
        soup : HTML code from which the Email header can be obtained.
        """
        fheader = fcontent[header_start_line_nr:header_end_line_nr]
        header = {}

        for lnr in range(len(fheader)):
            line = fheader[lnr]
            # get header keyword and value
            if re.match(r"\S+:\s+\S+", line):
                key = line.split(":")[0]
                value = line.replace(key + ":", "").strip().rstrip("\n")
                header[key.lower()] = value

        return header

    def _get_body_from_pipermail_file(
        self,
        fcontent: List[str],
        body_start_line_nr: int,
    ) -> str:
        # TODO re-write using email.parser.Parser
        body_end_line_nr = self.find_end_of_body(fcontent, body_start_line_nr)
        # get body content
        body = fcontent[body_start_line_nr:body_end_line_nr]
        # remove empty lines and join into one string
        body = ("\n").join([line for line in body if len(line) > 1])
        return body

    def find_start_of_header(
        self,
        fcontent: List[str],
        header_end_line_nr: int,
    ) -> int:
        header_start_line_nr = None

        for i in range(200):  # 200 lines up just to make sure...
            if fcontent[header_end_line_nr - i - 1] == "":
                header_start_line_nr = header_end_line_nr - i + 1
                break

        return header_start_line_nr

    def find_end_of_body(
        self,
        fcontent: List[str],
        body_start_line_nr: int,
    ) -> int:
        found = False
        line_nr = body_start_line_nr + 2

        while found is False:
            line_nr += 1
            if line_nr >= len(fcontent):
                body_end_line_nr = -1
                found = True
            elif fcontent[line_nr].startswith("Message-ID:"):
                for i in range(200):
                    if "From:" in fcontent[line_nr - i]:
                        body_end_line_nr = line_nr - i - 2
                        found = True
                        break

        return body_end_line_nr


class PipermailMailList(AbstractMailList):
    """
    This class handles the scraping of a all public Emails contained in a single
    mailing list in the Pipermail 0.09 format.
    This is done by downloading the gzip'd file for each month of a year in which
    an email was send to the mailing list.

    Parameters
    ----------
    name : The name of the list (e.g. public-2018-permissions-ws, ...)
    source : Contains the information of the location of the mailing list.
        It can be either an URL where the list or a path to the file(s).
    msgs : List of mboxMessage objects

    Example
    -------
    To scrape a ICANN mailing list from an URL and store it in
    run-time memory, we do the following

    >>> mlist = PipermailMailList.from_url(
    >>>     name="alac",
    >>>     url="https://mm.icann.org/pipermail/alac",
    >>>     select={
    >>>         "years": 2015,
    >>>         "months": "August",
    >>>         "fields": "header",
    >>>     },
    >>> )

    To save it as ``*.mbox`` file we do the following
    >>> mlist.to_mbox(path_to_file)
    """

    @classmethod
    def from_url(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = {"fields": "total"},
        instant_save: Optional[bool] = True,
    ) -> "PipermailMailList":
        """Docstring in `AbstractMailList`."""
        if "fields" not in list(select.keys()):
            select["fields"] = "total"
        period_urls = cls.get_period_urls(url, select)
        return cls.from_period_urls(
            name,
            url,
            period_urls,
            select["fields"],
            instant_save,
        )

    @classmethod
    def from_messages(
        cls,
        name: str,
        url: str,
        messages: MailList,
        fields: str = "total",
    ) -> "ListservMailList":
        """Docstring in `AbstractMailList`."""
        if not messages:
            messages = []
            logger.info(f"{name} initialised with no messages")
        return cls(name, url, messages)

    @classmethod
    def from_period_urls(
        cls,
        name: str,
        url: str,
        period_urls: List[str],
        fields: str = "total",
        instant_save: Optional[bool] = True,
    ) -> "PipermailMailList":
        """
        Parameters
        ----------
        """
        msg_parser = PipermailMessageParser(website=False)
        msgs = []
        for period_url in tqdm(period_urls, ascii=True, desc=name):
            file = requests.get(
                period_url,
                verify=os.path.join(CONFIG.config_path, "icann_certificate.pem"),
            )

            try:
                fcontent = gzip.decompress(file.content).decode("utf-8")
            except Exception:
                print(f"File {period_url} in {name} could not be decoded")
                continue

            fcontent = fcontent.split("\n")
            header_end_line_nrs = [
                idx + 1
                for idx, fl in enumerate(fcontent)
                if fl.startswith("Message-ID:")
            ]
            for header_end_line_nr in header_end_line_nrs:
                msgs.append(
                    msg_parser.from_pipermail_file(
                        name, fcontent, header_end_line_nr, fields
                    )
                )
                if (len(msgs) > 1e3) and (instant_save):
                    bio.mlist_to_mbox(
                        msgs,
                        CONFIG.mail_path + "ICANN/",
                        name,
                        "a",
                    )
                    msgs = []

        return cls(name, url, msgs)

    @classmethod
    def from_mbox(cls, name: str, filepath: str) -> "PipermailMailList":
        """Docstring in `AbstractMailList`."""
        msgs = bio.mlist_from_mbox(filepath)
        return cls(name, filepath, msgs)

    @classmethod
    def get_period_urls(cls, url: str, select: Optional[dict] = None) -> List[str]:
        """
        All messages within a certain period (e.g. January 2021).

        Parameters
        ----------
        url : URL to the Pipermail list.
        select : Selection criteria that can filter messages by:
            - content, i.e. header and/or body
            - period, i.e. written in a certain year and month
        """
        # create dictionary where keys are a period and values the url
        periods, urls_of_periods = cls.get_all_periods_and_their_urls(url)

        if any(period in list(select.keys()) for period in ["years", "months"]):
            for key, value in select.items():
                if key == "years":
                    cond = lambda x: int(re.findall(r"\d{4}", x)[0])
                elif key == "months":
                    cond = lambda x: x.split(" ")[0]
                else:
                    continue

                periodquants = [cond(period) for period in periods]

                indices = PipermailMailList.get_index_of_elements_in_selection(
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
        Pipermail groups messages into monthly time bundles. This method
        obtains all the URLs of time bundles and are downaloadable as gzip'd files.

        Returns
        -------
        Returns a tuple of two lists that look like:
        (['April 2017', 'January 2001', ...], ['ulr1', 'url2', ...])
        """
        # wait between loading messages, for politeness
        time.sleep(0.5)
        soup = get_website_content(
            url,
            verify=os.path.join(CONFIG.config_path, "icann_certificate.pem"),
        )
        periods = []
        urls_of_periods = []

        if soup != "RequestException":
            rows = soup.select(f'a[href*=".txt.gz"]')
            for row in rows:
                filename = row.get("href")
                if filename.endswith(".txt.gz") is False:
                    continue
                year = re.findall(r"\d{4}", filename)[0]
                month = filename.split(".")[0].replace(f"{year}-", "")
                periods.append(f"{month} {year}")
                urls_of_periods.append(url + "/" + filename)

        return periods, urls_of_periods

    @staticmethod
    def get_name_from_url(url: str) -> str:
        """Get name of mailing list."""
        return url.split("/")[-1]


class PipermailMailListDomain:
    def __init__(self, name: str, lists: List[Union[AbstractMailList, str]]):
        self.name = name
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
    def from_mailing_lists(
        cls,
        name: str,
        url_mailing_lists: Union[List[str], List[PipermailMailList]],
        select: Optional[dict] = {"fields": "total"},
        instant_save: Optional[bool] = True,
    ) -> "PipermailMailListDomain":
        """ """
        if isinstance(url_mailing_lists[0], str):
            lists = []
            for mlist_url in url_mailing_lists:
                mlist_name = PipermailMailList.get_name_from_url(mlist_url)
                mlist = PipermailMailList.from_url(
                    name=mlist_name,
                    url=mlist_url,
                    select=select,
                    instant_save=instant_save,
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
        return cls(name, lists)


def text_for_selector(soup: BeautifulSoup, selector: str):
    """
    Filter out header or body field from website and return them as utf-8 string.
    """
    results = soup.select(selector)
    if results:
        result = results[0].get_text(strip=True)
    else:
        result = ""
        logger.debug("No matching text for selector %s", selector)

    return str(result)


def parse_dfn_header(header_text):
    header_texts = str(header_text).split(":", 1)
    if len(header_texts) == 2:
        return header_texts[1]
    else:
        logger.debug("Split failed on %s", header_text)
        return ""
