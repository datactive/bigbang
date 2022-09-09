import os
import tempfile
from pathlib import Path
from unittest import mock
import shutil

import pytest
import yaml

import bigbang
from bigbang.ingress import (
    PipermailMessageParser,
    PipermailMailList,
    PipermailMailListDomain,
)
from config.config import CONFIG

url_mlistdom = "https://mm.icann.org/pipermail/"
url_list = url_mlistdom + "ssr2-review"
url_message = url_mlistdom + "ssr2-review/2021-October/002465.html"


class TestPipermailMessageParser:
    @pytest.fixture(name="msg", scope="module")
    def get_message(self):
        msg_parser = PipermailMessageParser(
            website=True,
        )
        msg = msg_parser.from_url(
            list_name="public-testtwf",
            url=url_message,
            fields="total",
        )
        return msg

    def test__message_content(self, msg):
        lines = msg.get_payload()  # .split("C")[1].split("=")[0]
        assert "I have been working on an update" in lines.split("\n")[0]
        assert msg["Subject"] == "Test the Web Forward Documentation Update"
        assert msg["From"] == "James Graham <james@hoppipolla.co.uk>"
        assert msg["To"] == '"public-testtwf@w3.org" <public-testtwf@w3.org>'
        assert msg["Date"] == "Tue, 02 Sep 2014 17:37:11 +0100"
        assert msg["Content-Type"] == 'text/plain; charset="utf-8"'

    def test__only_header_from_url(self):
        msg_parser = PipermailMessageParser(website=True)
        msg = msg_parser.from_url(
            list_name="public-testtwf",
            url=url_message,
            fields="header",
        )
        assert msg.get_payload() is None

    def test__only_body_from_url(self):
        msg_parser = PipermailMessageParser(website=True)
        msg = msg_parser.from_url(
            list_name="public-testtwf",
            url=url_message,
            fields="body",
        )
        assert str(msg["Subject"]) == "None"

    def test__to_dict(self, msg):
        dic = PipermailMessageParser.to_dict(msg)
        assert len(list(dic.keys())) == 11


class TestPipermailMailList:
    @pytest.fixture(name="mlist", scope="module")
    def get_mailinglist_from_url(self):
        mlist = PipermailMailList.from_url(
            name="ssr2-review",
            url=url_list,
            select={
                "years": 2014,
                "fields": "header",
            },
        )
        return mlist

    def test__get_mailinglist_from_messages(self):
        msgs_urls = [
            "https://mm.icann.org/pipermail/ssr2-review/2021-October/002465.html",
            "https://mm.icann.org/pipermail/ssr2-review/2021-October/002466.html",
        ]
        mlist = PipermailMailList.from_messages(
            name="ssr2-review",
            url=url_list,
            messages=msgs_urls,
        )
        assert len(mlist.messages) == 2

    def test__mailinglist_content(self, mlist):
        assert mlist.name == "ssr2-review"
        assert mlist.source == url_list
        assert len(mlist) == 14
        assert (
            mlist.messages[0]["Subject"]
            == "Re: Test the Web Forward Documentation Update"
        )

    def test__to_dict(self, mlist):
        dic = mlist.to_dict()
        assert len(list(dic.keys())) == 9
        assert len(dic[list(dic.keys())[0]]) == 14


