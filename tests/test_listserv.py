import pytest

from bigbang.listserv import ListservArchive, ListservList, ListservMessage

url_archive = "https://list.etsi.org/scripts/wa.exe?"
url_list = url_archive + "A0=3GPP_TSG_CT_WG6"
url_message = url_archive + "A2=ind2101A&L=3GPP_TSG_CT_WG6&O=D&P=1870"


class TestListservMessage:
    @pytest.fixture(name="msg", scope="module")
    def test__from_url(self):
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


class TestListservList:
    @pytest.fixture(name="mlist", scope="module")
    def test__from_url(self):
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


class TestListservArchive:
    @pytest.fixture(name="arch", scope="session")
    def test__from_url(self):
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
