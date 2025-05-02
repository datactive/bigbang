import os
import tempfile
from pathlib import Path
from unittest import mock
import shutil

import pytest
import yaml

import bigbang
from bigbang.ingress import (
    ListservMessageParser,
    ListservMailList,
    ListservMailListDomain,
)
from bigbang.ingress.utils import get_login_from_terminal
from bigbang.config import CONFIG

dir_temp = tempfile.gettempdir()
url_mlistdom = "https://listserv.ieee.org/cgi-bin/wa?"
url_list = url_mlistdom + "A0=IEEE-TEST"
url_message = url_mlistdom + "A2=IEEE-TEST;52220ef8.1511d&S="
file_temp_mbox = dir_temp + "/listserv.mbox"
file_auth = CONFIG.config_path + "authentication.yaml"
auth_key_mock = {"username": "bla", "password": "bla"}


class TestListservMessageParser:
    @pytest.mark.skipif(
        not os.path.isfile(file_auth),
        reason="Key to log into LISTSERV could not be found",
    )
    def test__from_url_with_login(self):
        with open(file_auth, "r") as stream:
            auth_key = yaml.safe_load(stream)
        msg_parser = ListservMessageParser(
            website=True,
            url_login="https://listserv.ieee.org/cgi-bin/wa?LOGON",
            url_pref="https://listserv.ieee.org/cgi-bin/wa?PREF",
            login=auth_key,
        )
        msg = msg_parser.from_url(
            list_name="IEEE-TEST",
            url=url_message,
            fields="total",
        )
        print(list(msg.keys()))
        assert msg["from"] == "iceeng-10"
        assert msg["in-reply-to"] is None

    @pytest.fixture(name="msg", scope="module")
    def get_message(self):
        msg_parser = ListservMessageParser(
            website=True,
            url_login="https://listserv.ieee.org/cgi-bin/wa?LOGON",
            url_pref="https://listserv.ieee.org/cgi-bin/wa?PREF",
            login=auth_key_mock,
        )
        msg = msg_parser.from_url(
            list_name="IEEE-TEST",
            url=url_message,
            fields="total",
        )
        return msg

    def test__message_content(self, msg):
        line = msg.get_payload().split("C")[1].split("=")[0]
        assert (
            line
            == "onference Announcement: Full Paper Submission Deadline (December 31, 2015)\n"
        )
        assert (
            msg["subject"]
            == '"10th International Conference on Electrical Engineering (ICEENG\'10)"'
        )
        assert msg["from"] == "iceeng-10"
        assert msg["to"] is None
        assert msg["date"] == "Mon, 23 Nov 2015 11:00:37 +0000"
        assert (
            msg["Content-Type"]
            == 'text/plain; charset="utf-8"; Content-Type="multipart/mixed"'
        )

    def test__only_header_from_url(self):
        msg_parser = ListservMessageParser(
            website=True,
            url_login="https://listserv.ieee.org/cgi-bin/wa?LOGON",
            url_pref="https://listserv.ieee.org/cgi-bin/wa?PREF",
            login=auth_key_mock,
        )
        msg = msg_parser.from_url(
            list_name="IEEE-TEST",
            url=url_message,
            fields="header",
        )
        assert msg.get_payload() is None

    def test__only_body_from_url(self):
        msg_parser = ListservMessageParser(
            website=True,
            url_login="https://listserv.ieee.org/cgi-bin/wa?LOGON",
            url_pref="https://listserv.ieee.org/cgi-bin/wa?PREF",
            login=auth_key_mock,
        )
        msg = msg_parser.from_url(
            list_name="IEEE-TEST",
            url=url_message,
            fields="body",
        )
        assert str(msg["subject"]) == "None"

    def test__to_dict(self, msg):
        dic = ListservMessageParser.to_dict(msg)
        assert len(list(dic.keys())) == 9

    def test__to_mbox(self, msg):
        ListservMessageParser.to_mbox(msg, filepath=file_temp_mbox)
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) == 75
        assert lines[1] == "Content-Transfer-Encoding: quoted-printable\n"
        f.close()
        Path(file_temp_mbox).unlink()


class TestListservMailList:
    @pytest.mark.skipif(
        not os.path.isfile(file_auth),
        reason="Key to log into LISTSERV could not be found",
    )
    def test__from_url_with_login(self):
        with open(file_auth, "r") as stream:
            auth_key = yaml.safe_load(stream)
        mlist = ListservMailList.from_url(
            name="IEEE-TEST",
            url=url_list,
            select={
                "fields": "header",
            },
            url_login="https://listserv.ieee.org/cgi-bin/wa?LOGON",
            url_pref="https://listserv.ieee.org/cgi-bin/wa?PREF",
            login=auth_key,
        )
        froms = list(set([msg["from"] for msg in mlist.messages]))
        assert '"Gilberto Santiago"' in froms
        tos = list(set([msg["to"] for msg in mlist.messages]))
        assert [None] == tos

    @pytest.fixture(name="mlist", scope="module")
    def get_maillist_from_url(self):
        mlist = ListservMailList.from_url(
            name="IEEE-TEST",
            url=url_list,
            select={
                "fields": "header",
            },
            login=auth_key_mock,
        )
        return mlist

    def test__get_maillist_from_messages(self):
        msgs_urls = [
            "https://listserv.ieee.org/cgi-bin/wa?A2=IEEE-TEST;a57724f6.2105a",
            "https://listserv.ieee.org/cgi-bin/wa?A2=IEEE-TEST;fc0a9fdd.2105b",
        ]
        mlist = ListservMailList.from_messages(
            name="IEEE-TEST",
            url=url_list,
            messages=msgs_urls,
            login=auth_key_mock,
        )
        assert len(mlist.messages) == 2

    def test__mailinglist_content(self, mlist):
        assert mlist.name == "IEEE-TEST"
        assert mlist.source == url_list
        # On 08/04/22 the mailing list contained 95 Emails.
        assert len(mlist) >= 95
        subjects = [msg["subject"] for msg in mlist.messages]
        assert (
            '"10th International Conference on Electrical Engineering (ICEENG\'10)"'
            in subjects
        )

    def test__to_dict(self, mlist):
        dic = mlist.to_dict()
        # On 08/04/22 the mailing list had 8 (header fields + body).
        assert len(list(dic.keys())) == 8
        # On 08/04/22 the mailing list contained 95 Emails.
        assert len(dic[list(dic.keys())[0]]) >= 95


class TestListservMailListDomain:
    @pytest.fixture(name="mlistdom", scope="session")
    def get_maillistdomain(self):
        mlistdom = ListservMailListDomain.from_mailing_lists(
            name="IEEE",
            url_root=url_mlistdom,
            url_mailing_lists=[
                "https://listserv.ieee.org/cgi-bin/wa?A0=STDS-802-15-15",
                "https://listserv.ieee.org/cgi-bin/wa?A0=STDS-802-15-14",
            ],
            select={
                "fields": "header",
            },
            url_login="https://listserv.ieee.org/cgi-bin/wa?LOGON",
            url_pref="https://listserv.ieee.org/cgi-bin/wa?PREF",
            login=auth_key_mock,
            instant_save=False,
            only_mlist_urls=False,
        )
        return mlistdom

    def test__maillistdomain_content(self, mlistdom):
        assert mlistdom.name == "IEEE"
        assert mlistdom.url == url_mlistdom
        assert len(mlistdom) == 2
        assert any([len(mlist) > 26 for mlist in mlistdom.lists])
        mlist_names = [mlist.name for mlist in mlistdom.lists]
        assert "STDS-802-15-15" in mlist_names
        assert "STDS-802-15-14" in mlist_names

    def test__to_dict(self, mlistdom):
        dic = mlistdom.to_dict()
        # On 08/04/22 the mlistdom had 9 (header fields + body).
        assert len(list(dic.keys())) == 9
        # On 08/04/22 the mlistdom contained 95 Emails.
        assert len(dic[list(dic.keys())[0]]) >= 57


@mock.patch("bigbang.ingress.utils.ask_for_input", return_value="check")
def test__get_login_from_terminal(input):
    """test if login keys will be documented"""
    file_auth = dir_temp + "/authentication.yaml"
    _, _ = get_login_from_terminal(username=None, password=None, file_auth=file_auth)
    f = open(file_auth, "r")
    lines = f.readlines()
    assert lines[0].strip("\n") == "username: 'check'"
    assert lines[1].strip("\n") == "password: 'check'"
    os.remove(file_auth)
