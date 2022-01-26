import copy
import datetime
import email
import logging
import mailbox
import os
import re
from mailbox import mboxMessage
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx
import numpy as np
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from config.config import CONFIG

import bigbang.bigbang_io as bio
from bigbang.utils import (
    get_paths_to_files_in_directory,
    get_paths_to_dirs_in_directory,
)
from bigbang.analysis.utils import (
    get_index_of_msgs_with_subject,
    get_index_of_msgs_with_datetime,
)

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
logging.basicConfig(
    filename=directory_project + "/listserv.analysis.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)

# Turn off pandas SettingWithCopyWarning warning
pd.options.mode.chained_assignment = None

# Indicators that a message is a reply
reply_labels = [
    "Re:",
    "Re\xa0",
    "AW:",
    "=?utf-8?b?J+WbnuWkjTo=?=",
    "=?utf-8?b?J+etlOWkjTo=?=",
]
# =?utf-8?b?J++9llNSVkND?=


class ListservMailListWarning(BaseException):
    """Base class for ListservMailList class specific exceptions"""

    pass


class ListservMailListDomainWarning(BaseException):
    """Base class for ListservMailListDomain class specific exceptions"""

    pass


class EmailArchive:
    """
    Note
    ----

    Methods
    -------
    from_mbox()
    """

    def __init__(
        self,
        name: str,
        filepath: str,
        msgs: pd.DataFrame,
    ):
        self.name = name
        self.filepath = filepath
        self.df = msgs

    def __len__(self) -> int:
        """Get number of messsages within the mailing list."""
        return len(self.df.index.values)

    def __iter__(self):
        """Iterate over each message within the mailing list."""
        return iter(self.df.iterrows())

    @classmethod
    def from_mbox_file(
        cls,
        filepath: str,
        name: Optional[str] = None,
        include_body: bool = True,
    ) -> "EmailArchive":
        box = mailbox.mbox(filepath, create=False)
        mlist = []
        if include_body:
            for msg in list(box.values()):
                _msg = dict(msg)
                _msg["body"] = msg.get_payload()
                mlist.append(_msg)
        else:
            for msg in list(box.values()):
                _msg = dict(msg)
                mlist.append(_msg)
        return mlist

    @classmethod
    def from_mbox_directory(
        cls,
        folderpath: str,
        filedsc: str = ".mail$",
        name: Optional[str] = None,
        include_body: bool = True,
    ) -> "EmailArchive":
        filepaths = EmailArchive.get_filepaths(folderpath, filedsc)
        # read all messages
        mlist = []
        if include_body:
            for filepath in filepaths:
                mbox_content = mailbox.mbox(filepath, create=False)
                for msg in list(mbox_content.values()):
                    _msg = dict(msg)
                    _msg["body"] = msg.get_payload()
                    mlist.append(_msg)
        else:
            for filepath in filepaths:
                mbox_content = mailbox.mbox(filepath, create=False)
                for msg in list(mbox_content.values()):
                    _msg = dict(msg)
                    mlist.append(_msg)
        # make all dictionary keys lower case
        mlist = [{k.lower(): v for k, v in msg.items()} for msg in mlist]
        return mlist

    @staticmethod
    def get_filepaths(folderpath: str, filedsc: str = ".mail$") -> List[str]:
        """Get all file paths from directory recursively."""
        pattern = re.compile(filedsc)
        filepaths = []
        for root, dirs, filenames in os.walk(folderpath):
            for filename in filenames:
                if pattern.match(filename):
                    filepaths.append(root + filename)
        return filepaths
