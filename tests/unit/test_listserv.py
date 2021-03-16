import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

import bigbang
from bigbang import listserv
from bigbang.listserv import ListservArchive, ListservList, ListservMessage
from config.config import CONFIG

dir_temp = tempfile.gettempdir()
file_temp_mbox = dir_temp + "/listserv.mbox"
file_auth = CONFIG.config_path + "authentication.yaml"
auth_key_mock = {"username": "bla", "password": "bla"}


class TestListservList:
    @pytest.fixture(name="mlist", scope="module")
    def test__from_url_without_login(self):
        mlist = ListservList.from_listserv_directories(
            name="3GPP_TSG_SA_ITUT_AHG",
            directorypaths=[
                CONFIG.test_data_path + "3GPP/3GPP_TSG_SA_ITUT_AHG/"
            ],
        )
        assert mlist.name == "3GPP_TSG_SA_ITUT_AHG"
        assert len(mlist) == 25
        return mlist

    def test__first_message_header(self, mlist):
        msg = mlist.messages[0]
        assert (
            msg.subject
            == "Re: Update on ITU-T related activities needing attention"
        )
        assert msg.fromname == "Stephen Hayes"
        assert msg.fromaddr == "stephen.hayes@ERICSSON.COM"
        assert msg.toname == "Stephen Hayes"
        assert msg.toaddr == "stephen.hayes@ERICSSON.COM"
        assert msg.date == "Mon May  8 10:47:41 2017"

    def test__first_message_body(self, mlist):
        msg = mlist.messages[0]
        assert msg.body.split("\n")[3] == "Hi,"
        assert len(msg.body) == 24129

    def test__to_dict(self, mlist):
        dic = mlist.to_dict()
        assert len(list(dic.keys())) == 8
        assert len(dic[list(dic.keys())[0]]) == 25

    def test__to_pandas_dataframe(self, mlist):
        df = mlist.to_pandas_dataframe()
        assert len(df.columns.values) == 8
        assert len(df.index.values) == 25

    def test__to_mbox(self, mlist):
        mlist.to_mbox(dir_temp, filename=mlist.name)
        file_temp_mbox = f"{dir_temp}/{mlist.name}.mbox"
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) == 41623
        assert lines[21] == "d activities:\n"
        f.close()
        Path(file_temp_mbox).unlink()


class TestListservArchive:
    @pytest.fixture(name="arch", scope="session")
    def test__from_listserv_directory(self):
        arch = ListservArchive.from_listserv_directory(
            name="3GPP",
            directorypath=CONFIG.test_data_path + "3GPP/",
        )
        assert arch.name == "3GPP"
        mlist_names = [mlist.name for mlist in arch.lists]
        assert "3GPP_TSG_SA_ITUT_AHG" in mlist_names
        assert "3GPP_TSG_SA_WG2_MTCE" in mlist_names
        ahg_index = mlist_names.index("3GPP_TSG_SA_ITUT_AHG")
        mtce_index = mlist_names.index("3GPP_TSG_SA_WG2_MTCE")
        assert len(arch.lists[ahg_index]) == 25
        assert len(arch.lists[mtce_index]) == 57
        assert (
            arch.lists[mtce_index].messages[0].subject
            == "test email - please ignore"
        )
        return arch

    def test__to_dict(self, arch):
        dic = arch.to_dict()
        assert len(list(dic.keys())) == 9
        assert len(dic[list(dic.keys())[0]]) == 82

    def test__to_pandas_dataframe(self, arch):
        df = arch.to_pandas_dataframe()
        assert len(df.columns.values) == 9
        assert len(df.index.values) == 82

    def test__to_mbox(self, arch):
        arch.to_mbox(dir_temp)
        file_dic = {
            f"{dir_temp}/3GPP_TSG_SA_ITUT_AHG.mbox": 41623,
            f"{dir_temp}/3GPP_TSG_SA_WG2_MTCE.mbox": 61211,
        }
        for filepath, line_nr in file_dic.items():
            assert Path(filepath).is_file()
            f = open(filepath, "r")
            lines = f.readlines()
            assert line_nr == len(lines)
            f.close()
            Path(filepath).unlink()


@mock.patch("bigbang.listserv.ask_for_input", return_value="check")
def test__get_login_from_terminal(input):
    """ test if login keys will be documented """
    file_auth = dir_temp + "/authentication.yaml"
    _, _ = listserv.get_login_from_terminal(
        username=None, password=None, file_auth=file_auth
    )
    f = open(file_auth, "r")
    lines = f.readlines()
    assert lines[0].strip("\n") == "username: 'check'"
    assert lines[1].strip("\n") == "password: 'check'"
    os.remove(file_auth)
