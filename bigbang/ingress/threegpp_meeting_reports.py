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


class ThreeGPPWGArchiveWarning(BaseException):
    """Base class for ThreeGPPWGArchive class specific exceptions"""

    pass


class ThreeGPPWGArchive(AbstractMailList):
    """
    Parameters
    ----------
    """

    @classmethod
    def from_url(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = None,
    ) -> "ThreeGPPWGArchive":
        """Docstring in `AbstractMailList`."""
        meeting_urls = cls.get_meeting_urls(url, select)
        return cls.from_meeting_urls(
            name,
            url,
            meeting_urls,
            select["file_extensions"],
        )

    @classmethod
    def from_meeting_urls(
        cls,
        name: str,
        url: str,
        period_urls: List[str],
        fields: str = "total",
    ) -> "ThreeGPPWGArchive":
        """
        Parameters
        ----------
        """
        return cls(name, url, msgs)

    @classmethod
    def get_meeting_urls(
        cls, url: str, select: Optional[dict] = None,
    ) -> List[str]:
        """
        Parameters
        ----------
        """
        meeting_urls = cls.get_all_meeting_urls_and_dates(url, [])
        print(meeting_urls[:10])
        print(len(meeting_urls))

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

                indices = ThreeGPPWGArchive.get_index_of_elements_in_selection(
                    periodquants,
                    urls_of_periods,
                    value,
                )

                periods = [periods[idx] for idx in indices]
                urls_of_periods = [urls_of_periods[idx] for idx in indices]
        return urls_of_periods

    @staticmethod
    def get_all_meeting_urls_and_dates(
        url: str,
        meeting_urls: List[str] = [],
    ) -> Tuple[List[str], List[str]]:
        """
        Returns
        -------
        """
        # wait between loading messages, for politeness
        time.sleep(0.5)
        soup = get_website_content(url)
        hrefs = soup.select(f'a[href*="{url}"]')
        urls = [href.get("href") for href in hrefs]
        meeting_urls += urls

        for u in meeting_urls:
            if '.' not in url.split('/')[-1]:
                meeting_urls.remove(u)
                ThreeGPPWGArchive.get_all_meeting_urls_and_dates(u, meeting_urls)
        return meeting_urls


    @staticmethod
    def get_name_from_url(url: str) -> str:
        """Get name of mailing list."""
        return url.split('/')[-1]
