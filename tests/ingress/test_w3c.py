import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

import bigbang
from bigbang.ingress import (
    W3CMessageParser,
    W3CMailingList,
    W3CMailingListDomain,
)
from config.config import CONFIG

dir_temp = tempfile.gettempdir()
url_mlistdom = "https://lists.w3.org/Archives/Public/"
url_list = url_mlistdom + "public-test2/"
url_message = url_mlistdom + "public-test2/2012Sep/0000.html"
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


class TestW3CMailingList:
    @pytest.fixture(name="mlist", scope="module")
    def get_mailinglist_from_url(self):
        mlist = W3CMailingList.from_url(
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
        mlist = W3CMailingList.from_messages(
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
        assert len(lines) == 31
        assert (
            lines[5]
            == "Subject: Re: W3C TPAC 2019 - Will your Community Group meet in Fukuoka?\n"
        )
        f.close()
        Path(file_temp_mbox).unlink()


class TestW3CMailingListDomain:
    # def test__get_only_mlist_urls(self):
    #    arch = W3CMailingListDomain.from_url(
    #        name="W3C",
    #        url_root=url_mlistdom,
    #        select={
    #            "years": 2015,
    #            "months": "November",
    #        },
    #        instant_save=False,
    #        only_mlist_urls=True,
    #    )
    #    return arch

    @pytest.fixture(name="mlistdom", scope="session")
    def get_mailarchive(self):
        mlistdom = W3CMailingListDomain.from_mailing_lists(
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
        mlistdom = W3CMailingListDomain.from_mbox(
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

    def test__archive_content(self, mlistdom):
        assert mlistdom.name == "W3C"
        assert mlistdom.url == url_mlistdom
        assert len(mlistdom) == 1
        assert len(mlistdom.lists[0]) == 2
        assert (
            mlistdom.lists[0].messages[0]["Subject"]
            == "Re: Web Accessibility Issue"
        )

    def test__to_dict(self, mlistdom):
        dic = mlistdom.to_dict()
        assert len(list(dic.keys())) == 10
        assert len(dic[list(dic.keys())[0]]) == 2

    def test__to_mbox(self, mlistdom):
        mlistdom.to_mbox(dir_temp)
        file_dic = {
            f"{dir_temp}/wai-site-comments.mbox": 25,
        }
        for filepath, line_nr in file_dic.items():
            assert Path(filepath).is_file()
            f = open(filepath, "r")
            lines = f.readlines()
            lines = [ll for ll in lines if len(ll) > 1]
            assert line_nr == len(lines)
            f.close()
            Path(filepath).unlink()
