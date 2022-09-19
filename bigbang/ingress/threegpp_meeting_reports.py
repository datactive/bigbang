from tqdm import tqdm
import email
import logging
import os
import re
import subprocess
import time
import warnings
import tempfile
import zipfile
import textract
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import urllib.parse

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


    @classmethod
    def get_all_doc_urls(
        cls,
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
            return urls_doc[:]
        
        else:
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
            
            if len(urls_dir) > 0:
                return ThreeGPPWGArchive.get_all_doc_urls(
                    urls_dir[0],
                    urls_dir[1:],
                    urls_doc,
                    doc_limit,
                )
            else:
                return urls_doc[:]
   
    def to_txt_file(
        self,
        file_path=directory_project + "/threegpp_meetingreports_urls.txt",
    ):
        with open(file_path, 'w') as fp:
            for doc_url in self.doc_urls:
                fp.write("%s\n" % doc_url)

    def download_docs(self):
        self.doc_file_path = []
        for url in self.doc_urls:
            file = requests.get(url)
            file_name = ('_').join(urllib.parse.unquote(url).split('/')[-3:])
            file_path =  CONFIG.mail_path + file_name
            self.doc_file_path.append(file_path)
            try:
                open(file_path, 'wb').write(file.content)
            except Exception:
                print(f'Couldnt save: {url}')

    def unzip_docs(self):
        for dfp in self.doc_file_path:
            if (dfp.lower().endswith('zip')):
                try:
                    zipdata = zipfile.ZipFile(dfp)
                    zipinfos = zipdata.infolist()

                    for zipinfo in zipinfos:
                        zipinfo.filename = dfp.split('/')[-1].split('.')[0] + '_' + zipinfo.filename
                        zipdata.extract(zipinfo, path=CONFIG.mail_path)
                except Exception:
                    print(f"Doesnt work for {dfp}")

    def read_docs(self, keyterms: List[str]):
        self.docs_of_interest = []
        for dfp in self.doc_file_path:
            if (dfp.lower().endswith('zip')):
                continue
            else:
                try:
                    text = textract.process(dfp).decode("utf-8")
                    counts = text.count('objected')
                    if counts > 0:
                        self.docs_of_interest.append(dfp)
                        print(counts, dfp)
                except Exception:
                    print(f"Doesnt work for {dfp}")
            
            #elif url.lower().endswith('doc'):
            #elif url.lower().endswith('docx'):
            #elif url.lower().endswith('pdf'):
            #elif url.lower().endswith('rtf'):
            #elif url.lower().endswith('xls'):
            #elif url.lower().endswith('xlsx'):
            #elif url.lower().endswith('xlsm'):
            #elif url.lower().endswith('xml'):
            #elif url.lower().endswith('pptx'):
            #elif url.lower().endswith('htm'):
            #else:
            #    print(f'Dont know the format of {url}')
