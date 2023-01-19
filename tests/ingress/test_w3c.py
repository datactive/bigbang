import os
import tempfile
from pathlib import Path
from unittest import mock
import shutil

import pytest
import yaml

import bigbang
from bigbang.ingress import (
    W3CMessageParser,
    W3CMailList,
    W3CMailListDomain,
)
from bigbang.config import CONFIG

url_mlistdom = "https://lists.w3.org/Archives/Public/"
url_list = url_mlistdom + "public-testtwf/"
url_message = url_mlistdom + "public-testtwf/2014Sep/0000.html"


class TestW3CMessageParser:
    @pytest.fixture(name="msg", scope="module")
    def get_message(self):
        msg_parser = W3CMessageParser(
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
        msg_parser = W3CMessageParser(website=True)
        msg = msg_parser.from_url(
            list_name="public-testtwf",
            url=url_message,
            fields="header",
        )
        assert msg.get_payload() is None

    def test__only_body_from_url(self):
        msg_parser = W3CMessageParser(website=True)
        msg = msg_parser.from_url(
            list_name="public-testtwf",
            url=url_message,
            fields="body",
        )
        assert str(msg["Subject"]) == "None"

    def test__to_dict(self, msg):
        dic = W3CMessageParser.to_dict(msg)
        assert len(list(dic.keys())) == 11


class TestW3CMailList:
    @pytest.fixture(name="mlist", scope="module")
    def get_mailinglist_from_url(self):
        mlist = W3CMailList.from_url(
            name="public-testtwf",
            url=url_list,
            select={
                "years": 2014,
                "fields": "header",
            },
        )
        return mlist

    def test__get_mailinglist_from_messages(self):
        msgs_urls = [
            "https://lists.w3.org/Archives/Public/public-testtwf/2014Sep/0000.html",
            "https://lists.w3.org/Archives/Public/public-testtwf/2014Apr/0001.html",
        ]
        mlist = W3CMailList.from_messages(
            name="public-testtwf",
            url=url_list,
            messages=msgs_urls,
        )
        assert len(mlist.messages) == 2

    def test__mailinglist_content(self, mlist):
        assert mlist.name == "public-testtwf"
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


class TestW3CMailListDomain:
    @pytest.fixture(name="mlistdom", scope="session")
    def get_maillistdomain(self):
        mlistdom = W3CMailListDomain.from_mailing_lists(
            name="W3C",
            url_root=url_mlistdom,
            url_mailing_lists=[
                "https://lists.w3.org/Archives/Public/public-ixml/",
                "https://lists.w3.org/Archives/Public/public-traffic/",
                "https://lists.w3.org/Archives/Public/wai-site-comments/",
            ],
            select={
                "years": 2015,
                "months": "November",
                "fields": "header",
            },
            instant_save=False,
            only_mlist_urls=False,
        )
        return mlistdom

    def test__from_mbox(self):
        mlistdom = W3CMailListDomain.from_mbox(
            name="3GPP",
            directorypath=CONFIG.test_data_path + "3GPP_mbox/",
            filedsc="3GPP_TSG_*.mbox",
        )
        assert len(mlistdom) == 2
        names = [mlist.name for mlist in mlistdom.lists]
        index = names.index("3GPP_TSG_SA_WG4_EVS")
        assert len(mlistdom.lists[index]) == 50
        index = names.index("3GPP_TSG_RAN_WG4_NR-MIMO-OTA")
        assert len(mlistdom.lists[index]) == 59

    def test__maillistdomain_content(self, mlistdom):
        assert mlistdom.name == "W3C"
        assert mlistdom.url == url_mlistdom
        assert len(mlistdom) == 1
        assert len(mlistdom.lists[0]) == 2
        assert mlistdom.lists[0].messages[0]["Subject"] == "Re: Web Accessibility Issue"

    def test__to_dict(self, mlistdom):
        dic = mlistdom.to_dict()
        assert len(list(dic.keys())) == 10
        assert len(dic[list(dic.keys())[0]]) == 2
