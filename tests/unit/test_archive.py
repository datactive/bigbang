import email
import logging
import mailbox
import os
import pathlib
import re
import shutil
from pathlib import Path
import unittest

import networkx as nx
import pandas as pd
from testfixtures import LogCapture

import bigbang.archive as archive
import bigbang.mailman as mailman
import bigbang.parse as parse
import bigbang.process as process
import bigbang.utils as utils
import bigbang.w3crawl as w3crawl
from bigbang import repo_loader
from config.config import CONFIG

test_txt = ""
TEMP_DIR = os.path.join(CONFIG.test_data_path, "tmp")


class TestArchive(unittest.TestCase):
    def setUp(self):
        try:
            os.mkdir(TEMP_DIR)
        except FileExistsError:
            pass  # temporary directory already exists, that's cool

    def tearDown(self):
        shutil.rmtree(TEMP_DIR)

    def test__archive_directory(self):
        dir_path = archive.archive_directory(TEMP_DIR, "test_bigbang")
        Path(dir_path).rmdir()

    def test__load_data(self):
        data = archive.load_data(
            name="empty-archive-df",
            archive_dir=CONFIG.test_data_path,
            mbox=False,
        )
        assert len(data.columns.values) == 7
        assert len(data.index.values) == 0
        data = archive.load_data(
            name="https://www.just_a_test.org/empty-archive-df/",
            archive_dir=CONFIG.test_data_path,
            mbox=False,
        )
        assert len(data.columns.values) == 7
        assert len(data.index.values) == 0

    def test__open_list_archives(self):
        data = archive.open_list_archives(
            url="3GPP_TSG_SA_WG4_EVS.mbox",
            archive_dir=CONFIG.test_data_path + "3GPP_mbox/",
            mbox=True,
        )
        assert len(data.columns.values) == 6
        assert len(data.index.values) == 50
        data = archive.open_list_archives(
            url="3GPP_mbox",
            archive_dir=CONFIG.test_data_path,
            mbox=False,
        )
        assert len(data.columns.values) == 6
        assert len(data.index.values) == 108
