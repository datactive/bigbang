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


class ThreeGPPWGArchive():
    """
    Parameters
    ----------
    """

    def __init__(
        self,
        name: str,
        source: Union[List[str], str],
        doc_urls: List[str],
    ):
        self.name = name
        self.source = source
        self.doc_urls = doc_urls

    @classmethod
    def from_url(
        cls,
        name: str,
        url: str,
        select: Optional[dict] = None,
        doc_limit: Optional[int] = None,
    ) -> "ThreeGPPWGArchive":
        """Docstring in `AbstractMailList`."""
        doc_urls = cls.filter_doc_urls(url, select, doc_limit)
        print(len(doc_urls))
        return cls.from_doc_urls(
            name,
            url,
            doc_urls,
        )

    @classmethod
    def from_doc_urls(
        cls,
        name: str,
        url: str,
        doc_urls: List[str],
    ) -> "ThreeGPPWGArchive":
        """
        Parameters
        ----------
        """
        return cls(name, url, doc_urls)

    @classmethod
    def filter_doc_urls(
        cls,
        url: str,
        select: Optional[dict] = None,
        doc_limit: Optional[int] = None,
        keyterms: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Parameters
        ----------
        """
        urls_doc = cls.get_all_doc_urls(url, [], [], doc_limit)

        keyterms = [
            "meetingreport",
            "report",
            "_rep_",
            "rp_",
        ] 

        urls_doc_sel = [
            url
            for url in urls_doc
            if any([True if kt in url.lower() else False for kt in keyterms])
        ]

        return urls_doc_sel


    @staticmethod
    def get_all_doc_urls(
        url: str,
        urls_dir: List[str] = [],
        urls_doc: List[str] = [],
        doc_limit: Optional[int] = None,
    ) -> List[str]:
        """
        Returns
        -------
        """
        if len(urls_doc) >= doc_limit:
            return urls_doc
        
        # wait between loading messages, for politeness
        time.sleep(0.5)
        soup = get_website_content(url)
        
        if isinstance(soup, BeautifulSoup):
            hrefs = soup.select(f'a[href*="{url}"]')
            _urls = [href.get("href") for href in hrefs]
            _urls_dir = [u for u in _urls if '.' not in u.split('/')[-1]]
            _urls_doc = list(set(_urls) - set(_urls_dir))
            urls_dir += _urls_dir
            urls_doc += _urls_doc
        
        if len(urls_doc) <  doc_limit:
            for ud in urls_dir:
                urls_dir.remove(ud)
                ThreeGPPWGArchive.get_all_doc_urls(ud, urls_dir, urls_doc, doc_limit)
        return urls_doc
        


    @staticmethod
    def get_name_from_url(url: str) -> str:
        """Get name of mailing list."""
        return url.split('/')[-1]
