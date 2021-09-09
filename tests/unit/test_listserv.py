import os
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
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
file_temp_mbox = dir_temp + "/listserv.mbox"
file_auth = CONFIG.config_path + "authentication.yaml"
auth_key_mock = {"username": "bla", "password": "bla"}

@pytest.fixture(name="mlist", scope="module")
def get_mailinglist():
    mlist = ListservList.from_listserv_directories(
        name="3GPP_TSG_SA_ITUT_AHG",
        directorypaths=[
            CONFIG.test_data_path + "3GPP/3GPP_TSG_SA_ITUT_AHG/"
        ],
    )
    return mlist

@pytest.fixture(name="msg_parser", scope="module")
def get_message_parser():
    msg_parser = ListservMessageParser()
    return msg_parser

@pytest.fixture(name="msg", scope="module")
def get_message(msg_parser):
    file_path = CONFIG.test_data_path + \
        "3GPP/3GPP_TSG_SA_ITUT_AHG/3GPP_TSG_SA_ITUT_AHG.LOG1705B"
    msg = msg_parser.from_listserv_file(
        list_name="3GPP_TSG_SA_ITUT_AHG",
        file_path=file_path,
        header_start_line_nr=1,
        fields="total",
    )
    return msg

class TestListservMessageParser:

    def test__first_message_header(self, msg):
        assert msg["From"] == "Stephen Hayes <stephen.hayes@ERICSSON.COM>"
        assert msg["Reply-To"] == "Stephen Hayes <stephen.hayes@ERICSSON.COM>"
        assert (
            msg["In-Reply-To"]
            == "<3d326663df91466eaa406d2ac87bd662@PREWE13M05.ad.sprint.com>"
        )
        assert msg["Date"] == "Mon, 08 May 2017 10:47:41 +0000"

    def test__first_message_body(self, msg):
        assert msg.get_payload().split("\n")[3] == "Hi,"
        assert len(msg.get_payload()) == 24809

    def test__to_pandas_dataframe(self, msg_parser, msg):
        df = msg_parser.to_pandas_dataframe(msg)
        assert len(df.columns.values) == 12
        assert len(df.index.values) == 1

    def test__to_mbox(self, msg_parser, msg):
        file_temp_mbox = f"{dir_temp}/bigbang_test_listserv.mbox"
        msg_parser.to_mbox(msg, filepath=file_temp_mbox)
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) == 638
        assert "See my comments below.\n" in lines
        f.close()
        Path(file_temp_mbox).unlink()


class TestListservList:

    def test__from_mbox(self):
        mlist_name = "3GPP_TSG_SA_WG4_EVS"
        mlist = ListservList.from_mbox(
            name=mlist_name,
            filepath=CONFIG.test_data_path + f"3GPP_mbox/{mlist_name}.mbox",
        )
        assert len(mlist) == 50
        assert mlist.messages[0]["From"] == "Tomas =?utf-8?q?Toftg=C3=A5rd?= <tomas.toftgard@ERICSSON.COM>"
    
    def test__from_listserv_files(self):
        filepath = CONFIG.test_data_path + \
            "3GPP/3GPP_TSG_SA_ITUT_AHG/3GPP_TSG_SA_ITUT_AHG.LOG1703B"
        mlist = ListservList.from_listserv_files(
            name="3GPP_TSG_SA_ITUT_AHG",
            filepaths=[filepath],
        )
        assert len(mlist) == 1
        assert mlist.messages[0]["From"] == "Kevin Holley <kevin.holley@BT.COM>"

    def test__number_of_messages(self, mlist):
        assert len(mlist) == 25

    def test__to_dict(self, mlist):
        dic = mlist.to_dict()
        keys = list(dic.keys())
        lengths = [len(value) for value in dic.values()]
        assert len(keys) == 13
        assert all([diff == 0 for diff in np.diff(lengths)])
        assert lengths[0] == 25
    
    def test__to_mbox(self, mlist):
        mlist.to_mbox(dir_temp, filename=mlist.name)
        file_temp_mbox = f"{dir_temp}/{mlist.name}.mbox"
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) >= 48940
        assert "What do you think of the approach?\n" in lines
        f.close()
        Path(file_temp_mbox).unlink()

    def test__missing_date_in_message(self, mlist):
        """
        Test that when a message has no date show, a default value
        """
        msg = [
            msg
            for msg in mlist.messages
            if msg["Subject"] == "R: How to proceed with ITUT-AH"
        ][0]
        assert msg["Date"] is None
        ListservMessageParser().to_mbox(
            msg, filepath=f"{dir_temp}/msg_test.mbox"
        )
        file_temp_mbox = f"{dir_temp}/msg_test.mbox"
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) == 547
        assert "Inviato: mercoled=3DEC 15 marzo 2017 16:06\n" in lines
        f.close()
        Path(file_temp_mbox).unlink()


class TestListservArchive:

    def test__from_mbox(self):
        march = ListservArchive.from_mbox(
            name="3GPP_mbox_test",
            directorypath=CONFIG.test_data_path + "3GPP_mbox/",
        )
        mlist_names = [mlist.name for mlist in march.lists]
        mlist_index = mlist_names.index("3GPP_TSG_SA_WG4_EVS")
        assert len(march.lists) == 2
        assert len(march.lists[mlist_index].messages) == 50
        assert march.lists[mlist_index].messages[0]["From"] == "Tomas =?utf-8?q?Toftg=C3=A5rd?= <tomas.toftgard@ERICSSON.COM>"

    @pytest.fixture(name="arch", scope="session")
    def get_mailarchive(self):
        arch = ListservArchive.from_listserv_directory(
            name="3GPP",
            directorypath=CONFIG.test_data_path + "3GPP/",
        )
        return arch

    def test__mailinglist_in_archive(self, arch):
        assert arch.name == "3GPP"
        mlist_names = [mlist.name for mlist in arch.lists]
        assert "3GPP_TSG_SA_ITUT_AHG" in mlist_names
        assert "3GPP_TSG_SA_WG2_MTCE" in mlist_names
        ahg_index = mlist_names.index("3GPP_TSG_SA_ITUT_AHG")
        mtce_index = mlist_names.index("3GPP_TSG_SA_WG2_MTCE")
        global mlist_ahg_length, mlist_mtce_length
        mlist_ahg_length = len(arch.lists[ahg_index])
        mlist_mtce_length = len(arch.lists[mtce_index])
        assert mlist_ahg_length == 25
        assert mlist_mtce_length == 57

    def test__message_in_mailinglist_in_archive(self, arch):
        mlist_names = [mlist.name for mlist in arch.lists]
        mtce_index = mlist_names.index("3GPP_TSG_SA_WG2_MTCE")
        msg = [
            msg
            for msg in arch.lists[mtce_index].messages
            if msg["Subject"] == "test email - please ignore"
        ][0]
        assert msg["From"] == '"Jain, Puneet" <puneet.jain@INTEL.COM>'
        assert msg["Reply-To"] == '"Jain, Puneet" <puneet.jain@INTEL.COM>'
        assert msg["Date"] == "Thu, 28 Feb 2013 18:58:18 +0000"

    def test__to_dict(self, arch):
        dic = arch.to_dict()
        keys = list(dic.keys())
        lengths = [len(value) for value in dic.values()]
        assert len(keys) == 14
        assert all([diff == 0 for diff in np.diff(lengths)])
        assert lengths[0] == (mlist_ahg_length + mlist_mtce_length)

    def test__to_mbox(self, arch):
        arch.to_mbox(dir_temp)
        file_dic = {
            f"{dir_temp}/3GPP_TSG_SA_ITUT_AHG.mbox": 40000,
            f"{dir_temp}/3GPP_TSG_SA_WG2_MTCE.mbox": 60000,
        }
        for filepath, line_nr in file_dic.items():
            assert Path(filepath).is_file()
            f = open(filepath, "r")
            lines = f.readlines()
            assert line_nr < len(lines)
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
