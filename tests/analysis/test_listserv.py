import os
import tempfile
from pathlib import Path
from unittest import mock
from unittest import TestCase

import numpy as np
import pytest
import yaml

from bigbang.analysis.listserv import ListservArchive
from bigbang.analysis.listserv import ListservList

from config.config import CONFIG

dir_temp = tempfile.gettempdir()
file_temp_mbox = dir_temp + "/listserv.mbox"
file_auth = CONFIG.config_path + "authentication.yaml"
auth_key_mock = {"username": "bla", "password": "bla"}


@pytest.fixture(name="march", scope="module")
def get_mailingarchive():
    march = ListservArchive.from_mbox(
        name="3GPP",
        directorypath=CONFIG.test_data_path + "3GPP_mbox/",
        filedsc="3GPP_TSG_*",
    )
    march.df = march.df.dropna()
    return march


@pytest.fixture(name="mlist", scope="module")
def get_mailinglist():
    mlist = ListservList.from_mbox(
        name="3GPP_TSG_SA_WG4_EVS",
        filepath=CONFIG.test_data_path + "3GPP_mbox/3GPP_TSG_SA_WG4_EVS.mbox",
    )
    mlist.df = mlist.df.dropna()
    return mlist


class TestListservList:
    def test__to_percentage(self):
        abso = np.array([1, 3])
        perc = ListservList.to_percentage(abso)
        np.testing.assert_array_equal(perc, np.array([0.25, 0.75]))

    def test__get_name_localpart_domain(self):
        addr = '"Gabin, Frederic" <Frederic.Gabin@DOLBY.COM>'
        name, localpart, domain = ListservList.get_name_localpart_domain(addr)
        assert name == "gabin frederic"
        assert localpart == "frederic.gabin"
        assert domain == "dolby.com"

    def test__period_of_activity(self, mlist):
        datetimes = mlist.period_of_activity()
        years = [dt.year for dt in datetimes]
        assert years == [2020, 2021]

    def test__crop_by_year(self, mlist):
        _mlist = mlist.crop_by_year(2020)
        assert len(_mlist.df.index.values) == 3
        datetimes = _mlist.period_of_activity()
        years = [dt.year for dt in datetimes]
        assert years == [2020, 2020]

    def test__crop_by_address(self, mlist):
        _mlist = mlist.crop_by_address(
            header_field="from",
            per_address_field={"domain": ["samsung.com"]},
        )
        assert len(_mlist.df.index.values) == 1

    def test__crop_by_subject(self, mlist):
        _mlist = mlist.crop_by_subject(match="EVS SWG Sessions")
        assert len(_mlist.df.index.values) == 1

    def test__get_domains(self, mlist):
        domains = mlist.get_domains(
            header_fields=["comments-to"], return_counts=True
        )
        domains_comp = [
            "ericsson.com",
            "qti.qualcomm.com",
            "list.etsi.org",
            "usherbrooke.ca",
        ]
        for domain in domains["comments-to"]:
            assert domain[0] in domains_comp
            if domain[0] == "qti.qualcomm.com":
                assert domain[1] == 7
        domains = mlist.get_domains(
            header_fields=["from"], return_counts=False
        )
        domains_comp = [
            "samsung.com",
            "qti.qualcomm.com",
            "philips.com",
            "iis.fraunhofer.de",
            "ericsson.com",
            "usherbrooke.ca",
            "3gpp.org",
        ]
        assert set(domains["from"]) == set(domains_comp)

    def test__get_domainscount(self, mlist):
        domains = mlist.get_domainscount(
            header_fields=["comments-to"],
            per_year=True,
        )
        assert domains["comments-to"][2020] == 2
        assert domains["comments-to"][2021] == 3
        domains = mlist.get_domainscount(
            header_fields=["from"],
            per_year=False,
        )
        assert domains["from"] == 7

    def test__get_localparts(self, mlist):
        localparts = mlist.get_localparts(
            header_fields=["comments-to"],
            per_domain=True,
            return_counts=False,
        )
        assert localparts["comments-to"]["ericsson.com"] == ["tomas.toftgard"]
        assert set(localparts["comments-to"]["qti.qualcomm.com"]) == set(
            ["nleung", "ivarga"]
        )
        localparts = mlist.get_localparts(
            header_fields=["comments-to"],
            per_domain=False,
            return_counts=True,
        )
        localparts = list(map(list, zip(*localparts["comments-to"])))
        assert "3gpp_tsg_sa_wg4_video" in localparts[0]
        assert "ivarga" in localparts[0]
        assert "milan.jelinek" in localparts[0]
        assert set(localparts[1]) == set([1, 6, 3, 1, 1])

    def test__get_localpartscount(self, mlist):
        localparts = mlist.get_localpartscount(
            header_fields=["comments-to"],
            per_domain=True,
            per_year=False,
        )
        assert localparts["comments-to"]["list.etsi.org"] == 1
        assert localparts["comments-to"]["usherbrooke.ca"] == 1
        assert localparts["comments-to"]["qti.qualcomm.com"] == 2
        localparts = mlist.get_localpartscount(
            header_fields=["from"],
            per_domain=False,
            per_year=True,
        )
        assert localparts["from"][2020] == 3
        assert localparts["from"][2021] == 6

    def test__get_subjects(self, mlist):
        subjects = mlist.get_subjects()
        assert subjects == []  # as they are all replies

    def test__get_subjectscount(self, mlist):
        count = mlist.get_subjectscount()
        assert count == 0  # as they are all replies

    def test__get_messagescount(self, mlist):
        msgcount = mlist.get_messagescount()
        assert msgcount == 12
        msgcount = mlist.get_messagescount(
            header_fields=["comments-to"],
            per_address_field="domain",
            per_year=False,
        )
        assert msgcount["comments-to"]["list.etsi.org"] == 1
        assert msgcount["comments-to"]["usherbrooke.ca"] == 3
        assert msgcount["comments-to"]["qti.qualcomm.com"] == 7
        msgcount = mlist.get_messagescount(
            header_fields=["from"],
            per_address_field="localpart",
            per_year=True,
        )
        assert msgcount["from"][2020]["milan.jelinek"] == 1
        assert msgcount["from"][2021]["milan.jelinek"] == 2
        assert msgcount["from"][2021]["markus.multrus"] == 1

    def test__get_messagescount_per_timezone(self, mlist):
        msgcount = mlist.get_messagescount_per_timezone()
        assert msgcount["+00:00"] == 7
        assert msgcount["+02:00"] == 1
        assert msgcount["-04:00"] == 2
        assert msgcount["-05:00"] == 1

    def test__get_sender_receiver_dictionary(self, mlist):
        dic = mlist.get_sender_receiver_dictionary()
        dic_true = {
            "ericsson.com": {"usherbrooke.ca": 1, "qti.qualcomm.com": 1},
            "usherbrooke.ca": {"ericsson.com": 1, "qti.qualcomm.com": 2},
            "qti.qualcomm.com": {"usherbrooke.ca": 2},
            "philips.com": {"qti.qualcomm.com": 1, "philips.com": 1},
            "iis.fraunhofer.de": {"qti.qualcomm.com": 2},
            "3gpp.org": {"qti.qualcomm.com": 1},
            "samsung.com": {"list.etsi.org": 2},
        }
        for key1, value1 in dic.items():
            for key2, value2 in value1.items():
                assert dic_true[key1][key2] == value2


class TestListservArchive:
    def test__get_mlistscount_per_institution(self, march):
        dic = ListservArchive.get_mlistscount_per_institution(march)
        dic_true = {
            "QTI.QUALCOMM.COM": 2,
            "USHERBROOKE.CA": 1,
            "3GPP.ORG": 1,
            "IIS.FRAUNHOFER.DE": 1,
            "SAMSUNG.COM": 1,
            "ERICSSON.COM": 1,
            "KEYSIGHT.COM": 1,
            "VIVO.COM": 1,
            "PHILIPS.COM": 1,
            "SPIRENT.COM": 1,
            "MEDIATEK.COM": 1,
            "APPLE.COM": 1,
        }
        for key in dic.keys():
            assert dic[key] == dic_true[key]
