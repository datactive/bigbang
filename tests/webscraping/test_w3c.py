import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

import bigbang
from bigbang import listserv
from bigbang.w3c import (
    W3CList,
    W3CMessageParser,
)
from config.config import CONFIG

dir_temp = tempfile.gettempdir()
url_archive = "https://lists.w3.org/Archives/Public/"
url_list = url_archive + "public-test2/"
url_message = url_archive + "public-test2/2012Sep/0000.html"
file_temp_mbox = dir_temp + "/w3c.mbox"


class TestW3CMessageParser:
    @pytest.fixture(name="msg", scope="module")
    def get_message(self):
        msg_parser = W3CMessageParser(
            website=True,
        )
        msg = msg_parser.from_url(
            list_name="public-test2",
            url=url_message,
            fields="total",
        )
        return msg

    def test__message_content(self, msg):
        lines = msg.get_payload()  # .split("C")[1].split("=")[0]
        assert lines.split("\n")[0] == "Dear Community Group participant,"
        assert (
            msg["Subject"]
            == "Survey on Community and Business Group Experience [reminder]"
        )
        assert msg["From"] == "Coralie Mercier <coralie@w3.org>"
        assert (
            msg["To"]
            == '"team-community-process@w3.org" <team-community-process@w3.org>'
        )
        assert msg["Date"] == "Fri, 07 Sep 2012 00:50:51 +0200"
        assert msg["Content-Type"] == 'text/plain; charset="utf-8"'

    def test__only_header_from_url(self):
        msg_parser = W3CMessageParser(website=True)
        msg = msg_parser.from_url(
            list_name="public-test2",
            url=url_message,
            fields="header",
        )
        assert msg.get_payload() is None

    def test__only_body_from_url(self):
        msg_parser = W3CMessageParser(website=True)
        msg = msg_parser.from_url(
            list_name="public-test2",
            url=url_message,
            fields="body",
        )
        assert str(msg["Subject"]) == "None"

    def test__to_dict(self, msg):
        dic = W3CMessageParser.to_dict(msg)
        assert len(list(dic.keys())) == 11

    def test__to_mbox(self, msg):
        W3CMessageParser.to_mbox(msg, filepath=file_temp_mbox)
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) == 37
        assert lines[1] == 'Content-Type: text/plain; charset="utf-8"\n'
        f.close()
        Path(file_temp_mbox).unlink()


class TestW3CList:
    @pytest.fixture(name="mlist", scope="module")
    def get_mailinglist_from_url(self):
        mlist = W3CList.from_url(
            name="public-test2",
            url=url_list,
            select={
                "years": 2019,
                "fields": "header",
            },
        )
        return mlist

    def test__get_mailinglist_from_messages(self):
        msgs_urls = [
            "https://lists.w3.org/Archives/Public/public-test2/2019Apr/0000.html",
            "https://lists.w3.org/Archives/Public/public-test2/2019Mar/0000.html",
        ]
        mlist = W3CList.from_messages(
            name="public-test2",
            url=url_list,
            messages=msgs_urls,
        )
        assert len(mlist.messages) == 2

    def test__mailinglist_content(self, mlist):
        assert mlist.name == "public-test2"
        assert mlist.source == url_list
        assert len(mlist) == 2
        assert (
            mlist.messages[0]["Subject"]
            == "Re: W3C TPAC 2019 - Will your Community Group meet in Fukuoka?"
        )

    def test__to_dict(self, mlist):
        dic = mlist.to_dict()
        assert len(list(dic.keys())) == 9
        assert len(dic[list(dic.keys())[0]]) == 2

    def test__to_mbox(self, mlist):
        mlist.to_mbox(dir_temp, filename=mlist.name)
        file_temp_mbox = f"{dir_temp}/{mlist.name}.mbox"
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        print(lines)
        assert len(lines) == 31
        assert (
            lines[5]
            == "Subject: Re: W3C TPAC 2019 - Will your Community Group meet in Fukuoka?\n"
        )
        f.close()
        Path(file_temp_mbox).unlink()
