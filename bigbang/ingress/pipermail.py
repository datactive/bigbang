from tqdm import tqdm
import email
import logging
import os
import re
import subprocess
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse

import numpy as np
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from config.config import CONFIG

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
)
from bigbang.utils import (
    get_paths_to_files_in_directory,
    get_paths_to_dirs_in_directory,
)

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



class PipermailMessageParser(AbstractMessageParser, email.parser.Parser):
    """
    This class handles the creation of an `mailbox.mboxMessage` object
    (using the from_*() methods) and its storage in various other file formats
    (using the to_*() methods) that can be saved on the local memory.

    Parameters
    ----------
    website : Set 'True' if messages are going to be scraped from websites,
        otherwise 'False' if read from local memory. This distinction needs to
        be made if missing messages should be added.
    url_pref : URL to the 'Preferences'/settings page.


    Example
    -------
    To create a Email message parser object, use the following syntax:
    >>> msg_parser = PipermailMessageParser(website=True)

    To obtain the Email message content and return it as `mboxMessage` object,
    you need to do the following:
    >>> msg = msg_parser.from_url(
    >>>     list_name="public-2018-permissions-ws",
    >>>     url="https://lists.w3.org/Archives/Public/public-2018-permissions-ws/2019May/0000.html",
    >>>     fields="total",
    >>> )
    """

    empty_header = {}

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
        self, list_name: str, url: str, soup: BeautifulSoup
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
            logger.exception(f"The message body of {url} could not be loaded.")
            return None


class PipermailMailList(AbstractMailList):
    """
    This class handles the scraping of a all public Emails contained in a single
    mailing list in the pipermail format.
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
    ) -> "PipermailMailList":
        """Docstring in `AbstractMailList`."""
        if "fields" not in list(select.keys()):
            select["fields"] = "total"
        period_urls = cls.get_period_urls(url, select)
        print("period_urls", period_urls)
        return cls.from_periods(
            name,
            url,
            period_urls,
            select["fields"],
        )

    @classmethod
    def from_periods(
        cls,
        name: str,
        url: str,
        messages: Union[List[str], MailList],
        fields: str = "total",
    ) -> "PipermailMailList":
        """Docstring in `AbstractMailList`."""
        if not messages:
            msgs = []
        elif isinstance(messages[0], str):
            msg_parser = PipermailMessageParser(
                website=True,
            )
            msgs = super().get_messages_from_urls(
                name, messages, msg_parser, fields
            )
        else:
            msgs = messages
        return cls(name, url, msgs)

    @classmethod
    def from_mbox(cls, name: str, filepath: str) -> "PipermailMailList":
        """Docstring in `AbstractMailList`."""
        msgs = bio.mlist_from_mbox(filepath)
        return cls(name, filepath, msgs)

    @classmethod
    def get_period_urls(
        cls, url: str, select: Optional[dict] = None
    ) -> List[str]:
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
            verify=f"{directory_project}/config/icann_certificate.pem",
        )
        periods = []
        urls_of_periods = []
        rows = soup.select(f'a[href*=".txt.gz"]')
        print("rows", rows)
        for row in rows:
            link = row.select("td:nth-of-type(1) a")
            if len(link) > 0:
                link = link[0]
            else:
                continue
            periods.append(link.text)
            urls_of_periods.append(url + "/" + link.get("href"))
        return periods, urls_of_periods

    @classmethod
    def get_messages_urls(cls, name: str, url: str) -> List[str]:
        """
        Parameters
        ----------
        name : Name of the Pipermail mailing list.
        url : URL to group of messages that are within the same period.

        Returns
        -------
        List of URLs from which `mboxMessage` can be initialized.
        """
        soup = get_website_content(url)
        if soup == "RequestException":
            return []
        else:
            a_tags = soup.select("div.messages-list a")
            if a_tags:
                a_tags = [
                    urljoin(url, a_tag.get("href"))
                    for a_tag in a_tags
                    if a_tag.get("href") is not None
                ]
            return a_tags

    @staticmethod
    def get_name_from_url(url: str) -> str:
        """Get name of mailing list."""
        name = ""
        url_position = -1
        while len(name) == 0:
            name = url.split("/")[url_position]
            url_position -= 1
        return name


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
