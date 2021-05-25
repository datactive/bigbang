import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

import bigbang
from bigbang import listserv
from bigbang.listserv import (
    ListservArchive,
    ListservList,
    ListservMessageParser,
)
from config.config import CONFIG

dir_temp = tempfile.gettempdir()
url_archive = "https://listserv.ieee.org/cgi-bin/wa?"
url_list = url_archive + "A0=IEEE-TEST"
url_message = url_archive + "A2=ind1511d&L=IEEE-TEST&P=67"
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
            login=auth_key,
        )
        msg = msg_parser.from_url(
            list_name="IEEE-TEST",
            url=url_message,
            fields="total",
        )
        assert msg["From"] == "iceeng-10"
        assert msg["To"] is None

    @pytest.fixture(name="msg", scope="module")
    def get_message(self):
        msg_parser = ListservMessageParser(
            website=True,
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
            msg["Subject"]
            == "10th International Conference on Electrical Engineering (ICEENG'10)"
        )
        assert msg["From"] == "iceeng-10"
        assert msg["To"] is None
        assert msg["Date"] == "Mon, 23 Nov 2015 11:00:37 +0000"
        assert (
            msg["Content-Type"]
            == 'text/plain; charset="utf-8"; Content-Type="multipart/mixed"'
        )

    def test__only_header_from_url(self):
        msg_parser = ListservMessageParser(
            website=True,
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
            login=auth_key_mock,
        )
        msg = msg_parser.from_url(
            list_name="IEEE-TEST",
            url=url_message,
            fields="body",
        )
        assert str(msg["Subject"]) == ""

    def test__to_dict(self, msg):
        dic = ListservMessageParser.to_dict(msg)
        assert len(list(dic.keys())) == 9

    def test__to_mbox(self, msg):
        ListservMessageParser.to_mbox(msg, file_temp_mbox)
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) == 75
        assert lines[1] == "Content-Transfer-Encoding: quoted-printable\n"
        f.close()
        Path(file_temp_mbox).unlink()


class TestListservList:
    @pytest.mark.skipif(
        not os.path.isfile(file_auth),
        reason="Key to log into LISTSERV could not be found",
    )
    def test__from_url_with_login(self):
        with open(file_auth, "r") as stream:
            auth_key = yaml.safe_load(stream)
        mlist = ListservList.from_url(
            name="IEEE-TEST",
            url=url_list,
            select={
                "years": 2015,
                "months": "November",
                "weeks": 4,
                "fields": "header",
            },
            login=auth_key,
        )
        assert mlist.messages[0]["From"] == "iceeng-10"
        assert mlist.messages[0]["To"] is None

    @pytest.fixture(name="mlist", scope="module")
    def get_mailinglist(self):
        mlist = ListservList.from_url(
            name="IEEE-TEST",
            url=url_list,
            select={
                "years": 2015,
                "fields": "header",
            },
            login=auth_key_mock,
        )
        return mlist

    def test__mailinglist_content(self, mlist):
        assert mlist.name == "IEEE-TEST"
        assert mlist.source == url_list
        assert len(mlist) == 1
        assert (
            mlist.messages[0]["Subject"]
            == "10th International Conference on Electrical Engineering (ICEENG'10)"
        )

    def test__to_dict(self, mlist):
        dic = mlist.to_dict()
        assert len(list(dic.keys())) == 7
        assert len(dic[list(dic.keys())[0]]) == 1

    def test__to_mbox(self, mlist):
        mlist.to_mbox(dir_temp, filename=mlist.name)
        file_temp_mbox = f"{dir_temp}/{mlist.name}.mbox"
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) == 18
        assert (
            lines[1]
            == "subject: 10th International Conference on Electrical Engineering (ICEENG'10)\n"
        )
        f.close()
        Path(file_temp_mbox).unlink()


class TestListservArchive:
    @pytest.fixture(name="arch", scope="session")
    def get_mailarchive(self):
        arch = ListservArchive.from_url(
            name="IEEE",
            url_root=url_archive,
            url_home=url_archive + "HOME",
            select={
                "years": 2015,
                "months": "November",
                "weeks": 4,
                "fields": "header",
            },
            login=auth_key_mock,
            instant_save=False,
            only_mlist_urls=False,
        )
        return arch

    def test__archive_content(self, arch):
        assert arch.name == "IEEE"
        assert arch.url == url_archive
        assert len(arch) == 1
        assert len(arch.lists[0]) == 1
        assert (
            arch.lists[0].messages[0]["Subject"]
            == "10th International Conference on Electrical Engineering (ICEENG'10)"
        )

    def test__to_dict(self, arch):
        dic = arch.to_dict()
        assert len(list(dic.keys())) == 7
        assert len(dic[list(dic.keys())[0]]) == 1

    def test__to_mbox(self, arch):
        arch.to_mbox(dir_temp)
        file_dic = {
            f"{dir_temp}/IEEE-TEST.mbox": 14,
        }
        for filepath, line_nr in file_dic.items():
            assert Path(filepath).is_file()
            f = open(filepath, "r")
            lines = f.readlines()
            lines = [ll for ll in lines if len(ll) > 1]
            assert line_nr == len(lines)
            f.close()
            Path(filepath).unlink()


@mock.patch("bigbang.listserv.ask_for_input", return_value="check")
def test__get_login_from_terminal(input):
    """test if login keys will be documented"""
    file_auth = dir_temp + "/authentication.yaml"
    _, _ = listserv.get_login_from_terminal(
        username=None, password=None, file_auth=file_auth
    )
    f = open(file_auth, "r")
    lines = f.readlines()
    assert lines[0].strip("\n") == "username: 'check'"
    assert lines[1].strip("\n") == "password: 'check'"
    os.remove(file_auth)
