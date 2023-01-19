import dateutil
import os
from pathlib import Path
import shutil
import unittest

import pandas as pd

import bigbang.archive as archive
from bigbang.config import CONFIG

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
            archive_name="3GPP_TSG_SA_WG4_EVS.mbox",
            archive_dir=CONFIG.test_data_path + "3GPP_mbox/",
            mbox=True,
        )
        assert len(data.columns.values) == 6
        assert len(data.index.values) == 50
        data = archive.open_list_archives(
            archive_name="3GPP_mbox",
            archive_dir=CONFIG.test_data_path,
            mbox=False,
        )
        assert len(data.columns.values) == 6
        assert len(data.index.values) == 108

        ## Testing add_affilation

        rel_email_affil = pd.DataFrame.from_records(
            [
                {
                    "email": "wangruixin@caict.ac.cn",
                    "affiliation": "TestOrg",
                    "min_date": dateutil.parser.parse("2019-04-18"),
                    "max_date": dateutil.parser.parse("2021-04-18"),
                }
            ]
        )

        arx = archive.Archive(data)

        arx.add_affiliation(rel_email_affil)

        assert (
            arx.data.loc["028c01d4fa43$13f2d060$3bd87120$@caict.ac.cn"]["affiliation"]
            == "TestOrg"
        )
        assert arx.data.loc["2019030112374440934718@caict.ac.cn"]["affiliation"] is None
