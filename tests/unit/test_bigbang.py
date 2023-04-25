import email
import logging
import mailbox
import os
import pathlib
import re
import shutil
import unittest

import networkx as nx
import pandas as pd
from testfixtures import LogCapture

import bigbang.archive as archive
import bigbang.ingress.mailman as mailman
import bigbang.parse as parse
import bigbang.analysis.process as process
import bigbang.utils as utils
from bigbang.analysis import repo_loader
from bigbang.config import CONFIG

test_txt = ""
TEMP_DIR = os.path.join(CONFIG.test_data_path, "tmp")


class TestGit(unittest.TestCase):
    def test_git_dependancy(self):
        repo_loader.get_repo(
            "https://github.com/sbenthall/bigbang.git",
            in_type="remote",
        )


class TestArchive(unittest.TestCase):
    def test_mailman_chain(self):
        name = "bigbang-dev-test.txt"

        # archive loaded from mbox
        arx = archive.Archive(name, archive_dir=CONFIG.test_data_path, mbox=True)

        arx.save("test.csv")

        # archive loaded from stored csv
        arx2 = archive.load("test.csv")

        print(arx.data.dtypes)
        print(arx.data.shape)

        self.assertTrue(
            arx.data.shape == arx2.data.shape,
            msg="Original and restored archives are different shapes",
        )

        self.assertTrue(
            (arx2.data.index == arx.data.index).all(),
            msg="Original and restored archives have nonidentical indices",
        )

        self.assertTrue(
            [t.get_num_messages() for t in arx.get_threads()] == [3, 1, 2],
            msg="Thread message count in mbox archive is off",
        )

        self.assertTrue(
            [t.get_num_messages() for t in arx2.get_threads()] == [3, 1, 2],
            msg="Thread message count in restored archive is off",
        )

        # smoke test entity resolution
        arx2.resolve_entities()

        os.remove("test.csv")

    def test_clean_message(self):
        name = "2001-November.txt"

        arx = archive.Archive(name, archive_dir=CONFIG.test_data_path, mbox=True)

        body = arx.data["Body"]["<E165uMn-0002IJ-00@spock.physics.mcgill.ca>"]

        self.assertTrue(
            "But seemingly it is even stranger than this." in body,
            msg="Selected wrong message",
        )

        self.assertTrue(
            "Is it a problem of lapack3.0 of of" in body,
            msg="Quoted text is not in uncleaned message",
        )

        self.assertTrue(
            "Is it a problem of lapack3.0 of of" not in utils.clean_message(body),
            msg="Quoted text is in cleaned message",
        )

    def test_email_entity_resolution(self):
        name = "2001-November.txt"

        arx = archive.Archive(name, archive_dir=CONFIG.test_data_path, mbox=True)

        e = process.resolve_sender_entities(arx.get_activity(resolved=False))

        utils.repartition_dataframe(arx.get_activity(), e)

        self.assertTrue(True, msg="email entity resolution crashed")


class TestMailParsing(unittest.TestCase):
    def test_split_references(self):
        refs = " <ye1y9ljtxwk.fsf@orange30.ex.ac.uk>\n\t<055701c16727$b57fed90$8fd6afcf@pixi.com>"
        split = parse.split_references(refs)
        self.assertTrue(len(split) == 2, msg=split)

    def test_name_email_parsing(self):
        from_header = "John_Doe (?) <John.Doe@example.com>"
        (raw_name, raw_email) = email.utils.parseaddr(from_header)
        normalized_email = parse.normalize_email_address(raw_email)
        self.assertTrue(
            normalized_email == "john.doe@example.com",
            msg="normalized email case incorrect",
        )

        clean_name = parse.clean_name(raw_name)
        self.assertTrue(clean_name == "John Doe", msg="name not fully cleaned")

        empty_name = parse.clean_name(" ")
        self.assertTrue(empty_name is None, msg="empty name not cleaned to None")

        tokenized_name = parse.tokenize_name(clean_name)
        self.assertTrue(
            tokenized_name == "doe john",
            msg="name not properly normalized and tokenized",
        )

        parse.tokenize_name(str("   "))
        self.assertTrue(empty_name is None, msg="empty name not tokenized to None")


class TestMailProcessing(unittest.TestCase):
    def test_from_header_distance(self):
        a = "Fernando.Perez at colorado.edu (Fernando.Perez at colorado.edu)"
        b = "Fernando.Perez at colorado.edu (Fernando.Perez@colorado.edu)"

        self.assertTrue(
            process.from_header_distance(a, b) == 0,
            msg="from_header_distance computing incorrect value",
        )

        a = ""
        b = ""


class TestUtils(unittest.TestCase):
    def test_labeled_blockmodel(self):
        g = nx.DiGraph()

        g.add_edge(0, 1)
        g.add_edge(0, 2)
        g.add_edge(0, 3)
        g.add_edge(0, 4)

        p = {"B": [1, 2, 3, 4], "A": [0]}

        bg = utils.labeled_blockmodel(g, p)

        self.assertTrue(
            list(bg.edges(data=True))[0][2]["weight"] == 4.0,
            msg="Incorrect edge weight in labeled blockmodel",
        )

        self.assertTrue(
            list(bg.edges()) == [("A", "B")],
            msg="Incorrected edges in labeled blockmodel",
        )
