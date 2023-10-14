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
import bigbang.ingress.mailman as mailman
from bigbang.config import CONFIG

test_txt = ""
TEMP_DIR = os.path.join(CONFIG.test_data_path, "tmp")


class TestMailman(unittest.TestCase):
    def setUp(self):
        try:
            os.mkdir(TEMP_DIR)
        except FileExistsError:
            pass  # temporary directory already exists, that's cool

    def tearDown(self):
        shutil.rmtree(TEMP_DIR)

    def test__collect_from_file(self):
        urls_file = CONFIG.test_data_path + "urls-test-file.txt"
        mailman.collect_from_file(urls_file)

    def test__provenance(self):
        test_list_name = "test-list-name"
        test_list_url = "https://example.com/test-list-url/"
        test_notes = "Test notes."
        mailman.populate_provenance(
            TEMP_DIR,
            list_name=test_list_name,
            list_url=test_list_url,
            notes=test_notes,
        )

        self.assertTrue(
            os.path.exists(os.path.join(TEMP_DIR, mailman.PROVENANCE_FILENAME)),
            msg="provenance file should have been created",
        )

        provenance = mailman.access_provenance(TEMP_DIR)
        self.assertTrue(provenance is not None, "provenance should be something")
        self.assertTrue(
            provenance["list"]["list_name"] == test_list_name,
            "list name should be in the provenance",
        )
        self.assertTrue(
            provenance["list"]["list_url"] == test_list_url,
            "list url should be in the provenance",
        )
        self.assertTrue(
            provenance["notes"] == test_notes,
            "notes should be in the provenance",
        )

        provenance["notes"] = "modified provenance"
        mailman.update_provenance(TEMP_DIR, provenance)
        provenance_next = mailman.access_provenance(TEMP_DIR)
        self.assertTrue(
            provenance_next["notes"] == "modified provenance",
            "confirm modified provenance",
        )

    def test__valid_urls(self):
        test_urls_path = os.path.join(CONFIG.test_data_path, "urls-test-file.txt")
        with LogCapture() as _l:
            urls = mailman.urls_to_collect(test_urls_path)
            self.assertTrue(
                "#ignored" not in urls, msg="failed to ignore a comment line"
            )
            self.assertTrue(
                "http://www.example.com/1" in urls,
                msg="failed to find valid url",
            )

            self.assertTrue(
                "http://www.example.com/2/" in urls,
                msg="failed to find valid url, whitespace strip issue",
            )
            self.assertTrue(
                "https://www.example.com/3/" in urls,
                msg="failed to find valid url, whitespace strip issue",
            )
            self.assertTrue("invalid.com" not in urls, msg="accepted invalid url")
            self.assertTrue(
                len(list(_l.actual())) == 2, msg="wrong number of log entries"
            )
            for fromwhere, level, msg in _l.actual():
                self.assertTrue(
                    level == "WARNING",
                    msg="logged something that wasn't a warning",
                )
                self.assertTrue(
                    len(urls) == 3, msg="wrong number of urls parsed from file"
                )

    def test__empty_list_compute_activity_issue_246(self):
        test_df_csv_path = os.path.join(CONFIG.test_data_path, "empty-archive-df.csv")
        df = pd.read_csv(test_df_csv_path)

        with self.assertRaises(archive.MissingDataException):
            empty_archive = archive.Archive(df)
            empty_archive.get_activity()

    def test__normalizer(self):
        browse_url = "https://mailarchive.ietf.org/arch/browse/ietf/"
        search_url = "https://mailarchive.ietf.org/arch/search/?email_list=ietf"
        random_url = "http://example.com"

        better_url = "https://www.ietf.org/mail-archive/text/ietf/"

        self.assertTrue(
            mailman.normalize_archives_url(browse_url) == better_url,
            msg="failed to normalize",
        )
        self.assertTrue(
            mailman.normalize_archives_url(search_url) == better_url,
            msg="failed to normalize",
        )
        self.assertTrue(
            mailman.normalize_archives_url(random_url) == random_url,
            msg="should not have changed other url",
        )

    def test__get_list_name(self):
        ietf_archive_url = "https://www.ietf.org/mail-archive/text/ietf/"
        w3c_archive_url = "https://lists.w3.org/Archives/Public/public-privacy/"
        random_url = "http://example.com"

        self.assertTrue(
            mailman.get_list_name(ietf_archive_url) == "ietf",
            msg="failed to grab ietf list name",
        )
        self.assertTrue(
            mailman.get_list_name(w3c_archive_url) == "public-privacy",
            msg="failed to grab w3c list name",
        )
        self.assertTrue(
            mailman.get_list_name(random_url) == random_url,
            msg="should not have changed other url",
        )

    def test__activity_summary(self):
        list_url = "https://lists.w3.org/Archives/Public/test-activity-summary/"
        activity_frame = mailman.open_activity_summary(
            list_url, archive_dir=CONFIG.test_data_path
        )

        self.assertTrue(
            str(type(activity_frame)) == "<class 'pandas.core.frame.DataFrame'>",
            msg="not a DataFrame?",
        )
        self.assertTrue(
            len(activity_frame.columns) == 1,
            msg="activity summary should have one column",
        )
