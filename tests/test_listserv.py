import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

import bigbang
from bigbang import listserv
from bigbang.listserv import ListservArchive, ListservList, ListservMessage

url_archive = "https://list.etsi.org/scripts/wa.exe?"
url_list = url_archive + "A0=3GPP_TSG_CT_WG6"
url_message = url_archive + "A2=ind2101A&L=3GPP_TSG_CT_WG6&O=D&P=1870"
file_auth = "../config/authentication.yaml"
dir_temp = tempfile.gettempdir()
file_temp_mbox = dir_temp + "/listserv.mbox"


class TestListservMessage:
    @pytest.mark.skipif(
        not os.path.isfile(file_auth),
        reason="Key to log into LISTSERV could not be found",
    )
    def test__from_url_with_login(self):
        with open(file_auth, "r") as stream:
            auth_key = yaml.safe_load(stream)
        msg = ListservMessage.from_url(
            list_name="3GPP_TSG_CT_WG6",
            url=url_message,
            fields="total",
            login=auth_key,
        )
        assert msg.fromaddr == "Kimmo.Kymalainen@ETSI.ORG"
        assert msg.toaddr == "Kimmo.Kymalainen@ETSI.ORG"

    @pytest.fixture(name="msg", scope="module")
    def test__from_url_without_login(self):
        msg = ListservMessage.from_url(
            list_name="3GPP_TSG_CT_WG6",
            url=url_message,
            fields="total",
        )
        assert msg.body.split(",")[0] == "Dear 3GPP CT people"
        assert msg.subject == "Happy New Year 2021"
        assert msg.fromname == "Kimmo Kymalainen"
        assert msg.fromaddr == "[log in to unmask]"
        assert msg.toname == "Kimmo Kymalainen"
        assert msg.toaddr == "[log in to unmask]"
        assert msg.date == "Tue Jan  5 12:15:30 2021"
        assert msg.contenttype == "multipart/related"
        return msg

    def test__only_header_from_url(self):
        msg = ListservMessage.from_url(
            list_name="3GPP_TSG_CT_WG6",
            url=url_message,
            fields="header",
        )
        assert msg.body is None

    def test__only_body_from_url(self):
        msg = ListservMessage.from_url(
            list_name="3GPP_TSG_CT_WG6",
            url=url_message,
            fields="body",
        )
        assert msg.subject is None

    def test__to_dict(self, msg):
        dic = msg.to_dict()
        assert len(list(dic.keys())) == 8

    def test__to_mbox(self, msg):
        msg.to_mbox(file_temp_mbox)
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) == 29
        assert (
            lines[1] == "From b'[log in to unmask]' Tue Jan  5 12:15:30 2021\n"
        )
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
            name="3GPP_TSG_CT_WG6",
            url=url_list,
            select={
                "years": 2021,
                "months": "January",
                "weeks": 1,
                "fields": "header",
            },
            login=auth_key,
        )
        assert mlist.messages[0].fromaddr == "Kimmo.Kymalainen@ETSI.ORG"
        assert mlist.messages[0].toaddr == "Kimmo.Kymalainen@ETSI.ORG"

    @pytest.fixture(name="mlist", scope="module")
    def test__from_url_without_login(self):
        mlist = ListservList.from_url(
            name="3GPP_TSG_CT_WG6",
            url=url_list,
            select={
                "years": 2021,
                "months": "January",
                "weeks": 1,
                "fields": "header",
            },
        )
        assert mlist.name == "3GPP_TSG_CT_WG6"
        assert mlist.source == url_list
        assert len(mlist) == 3
        assert mlist.messages[0].subject == "Happy New Year 2021"
        return mlist

    def test__to_dict(self, mlist):
        dic = mlist.to_dict()
        assert len(list(dic.keys())) == 8
        assert len(dic[list(dic.keys())[0]]) == 3

    def test__to_pandas_dataframe(self, mlist):
        df = mlist.to_pandas_dataframe()
        assert len(df.columns.values) == 8
        assert len(df.index.values) == 3

    def test__to_mbox(self, mlist):
        mlist.to_mbox(dir_temp, filename=mlist.name)
        file_temp_mbox = f"{dir_temp}/{mlist.name}.mbox"
        f = open(file_temp_mbox, "r")
        lines = f.readlines()
        assert len(lines) == 30
        assert (
            lines[21]
            == "From b'[log in to unmask]' Tue Jan  5 09:28:25 2021\n"
        )
        f.close()
        Path(file_temp_mbox).unlink()


class TestListservArchive:
    @pytest.mark.skipif(
        not os.path.isfile(file_auth),
        reason="Key to log into LISTSERV could not be found",
    )
    def test__from_url_with_login(self):
        with open(file_auth, "r") as stream:
            auth_key = yaml.safe_load(stream)
        arch = ListservArchive.from_url(
            name="3GPP",
            url_root=url_archive,
            url_home=url_archive + "HOME",
            select={
                "years": 2021,
                "months": "January",
                "weeks": 1,
                "fields": "header",
            },
            login=auth_key,
        )
        assert (
            arch.lists[0].messages[0].fromaddr == "Kimmo.Kymalainen@ETSI.ORG"
        )
        assert arch.lists[0].messages[0].toaddr == "Kimmo.Kymalainen@ETSI.ORG"

    @pytest.fixture(name="arch", scope="session")
    def test__from_url_wihout_login(self):
        arch = ListservArchive.from_url(
            name="3GPP",
            url_root=url_archive,
            url_home=url_archive + "HOME",
            select={
                "years": 2021,
                "months": "January",
                "weeks": 1,
                "fields": "header",
            },
        )
        assert arch.name == "3GPP"
        assert arch.url == url_archive
        assert len(arch) == 4
        assert len(arch.lists[0]) == 3
        assert arch.lists[0].messages[0].subject == "Happy New Year 2021"
        return arch

    def test__to_dict(self, arch):
        dic = arch.to_dict()
        assert len(list(dic.keys())) == 9
        assert len(dic[list(dic.keys())[0]]) == 40

    def test__to_pandas_dataframe(self, arch):
        df = arch.to_pandas_dataframe()
        assert len(df.columns.values) == 9
        assert len(df.index.values) == 40

    def test__to_mbox(self, arch):
        arch.to_mbox(dir_temp)
        file_dic = {
            f"{dir_temp}/3GPP_TSG_CT_WG6.mbox": 30,
            f"{dir_temp}/3GPP_TSG_RAN_WG3.mbox": 40,
            f"{dir_temp}/3GPP_TSG_RAN.mbox": 30,
            f"{dir_temp}/3GPP_TSG_RAN_WG4.mbox": 300,
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
