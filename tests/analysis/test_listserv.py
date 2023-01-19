import os
import tempfile
from pathlib import Path
from unittest import mock
from unittest import TestCase

import numpy as np
import pytest
import yaml

from bigbang.analysis.listserv import ListservMailListDomain
from bigbang.analysis.listserv import ListservMailList

from bigbang.config import CONFIG

dir_temp = tempfile.gettempdir()
file_temp_mbox = dir_temp + "/listserv.mbox"
file_auth = CONFIG.config_path + "authentication.yaml"
auth_key_mock = {"username": "bla", "password": "bla"}


@pytest.fixture(name="march", scope="module")
def get_mailingarchive():
    march = ListservMailListDomain.from_mbox(
        name="3GPP",
        directorypath=CONFIG.test_data_path + "3GPP_mbox/",
        filedsc="3GPP_TSG_*",
    )
    return march


@pytest.fixture(name="mlist", scope="module")
def get_mailinglist():
    mlist = ListservMailList.from_mbox(
        name="3GPP_TSG_SA_WG4_EVS",
        filepath=CONFIG.test_data_path + "3GPP_mbox/3GPP_TSG_SA_WG4_EVS.mbox",
    )
    return mlist


def test_dissection_of_address_header_field():
    filepath = CONFIG.test_data_path + "address_header_test_file.yaml"
    with open(filepath, "r") as stream:
        addresses = yaml.safe_load(stream)

    generator = ListservMailList.iterator_name_localpart_domain(list(addresses.keys()))
    assert (
        list(next(generator))
        == addresses['"xuxiaodong@chinamobile.com" <xuxiaodong@CHINAMOBILE.COM>']
    )
    assert list(next(generator)) == addresses["Jacob John <jacobjohn@MOTOROLA.COM>"]
    assert (
        list(next(generator))
        == addresses['"Wuyuchun (Wu Yuchun, Hisilicon)" <wuyuchun@HUAWEI.COM>']
    )
    assert (
        list(next(generator))
        == addresses["xingjinqiang@chinamobile.com xingjinqiang@chinamobile.com"]
    )
    assert list(next(generator)) == addresses["abdul rasheed m d rasheed@motorola.com"]
    assert (
        list(next(generator))
        == addresses[
            "fredrik =?utf-8?q?sundstr=c3=b6m?= fredrik.sundstrom@ericsson.com"
        ]
    )
    assert list(next(generator)) == addresses["guozhili guozhili@starpointcomm.com"]
    assert (
        list(next(generator))
        == addresses["=?utf-8?b?runjvc3lvkdnu6flrr4=?= zhangjibin@ecit.org.cn"]
    )
    replyto_sample = addresses[
        '"Yanyali (Yali)" <yanyali@HUAWEI.COM>, Guchunying <guchunying@HUAWEI.COM>, Ingbert Sigovich <Ingbert.Sigovich@ETSI.ORG>'
    ]
    assert list(next(generator)) == replyto_sample[0][1]
    assert list(next(generator)) == replyto_sample[1][2]
    assert list(next(generator)) == replyto_sample[2][3]


class TestListservMailList:
    def test__to_percentage(self):
        abso = np.array([1, 3])
        perc = ListservMailList.to_percentage(abso)
        np.testing.assert_array_equal(perc, np.array([0.25, 0.75]))

    def test__get_name_localpart_domain(self):
        addr = '"gabin frederic" <frederic.gabin@dolby.com>'
        name, localpart, domain = ListservMailList.get_name_localpart_domain(addr)
        assert name == "gabin frederic"
        assert localpart == "frederic.gabin"
        assert domain == "dolby.com"

    def test__period_of_activity(self, mlist):
        datetimes = mlist.period_of_activity()
        years = [dt.year for dt in datetimes]
        assert years == [2020, 2021]

    def test__crop_by_year(self, mlist):
        _mlist = mlist.crop_by_year(2020)
        assert len(_mlist.df.index.values) == 25
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
        _mlist = mlist.crop_by_subject(match="EVS SWG Sessions", place=0)
        assert len(_mlist.df.index.values) == 3

    def test__get_domains(self, mlist):
        domains = mlist.get_domains(
            header_fields=["comments-to"], return_msg_counts=True
        )
        domains_comp = [
            "ericsson.com",
            "qti.qualcomm.com",
            "list.etsi.org",
            "usherbrooke.ca",
            "philips.com",
        ]
        for domain in domains["comments-to"]:
            assert domain[0] in domains_comp
            if domain[0] == "qti.qualcomm.com":
                assert domain[1] == 8
        domains = mlist.get_domains(header_fields=["from"], return_msg_counts=False)
        domains_comp = [
            "samsung.com",
            "qti.qualcomm.com",
            "philips.com",
            "iis.fraunhofer.de",
            "ericsson.com",
            "usherbrooke.ca",
            "3gpp.org",
            "dolby.com",
            "qosound.com",
        ]
        assert set(domains["from"]) == set(domains_comp)

    def test__get_domainscount(self, mlist):
        domains = mlist.get_domainscount(
            header_fields=["comments-to"],
            per_year=True,
        )
        assert domains["comments-to"][2020] == 2
        assert domains["comments-to"][2021] == 4
        domains = mlist.get_domainscount(
            header_fields=["from"],
            per_year=False,
        )
        assert domains["from"] == 9

    def test__get_localparts(self, mlist):
        localparts = mlist.get_localparts(
            header_fields=["comments-to"],
            per_domain=True,
            return_msg_counts=False,
        )
        assert localparts["comments-to"]["ericsson.com"] == ["tomas.toftgard"]
        assert set(localparts["comments-to"]["qti.qualcomm.com"]) == set(
            ["nleung", "ivarga"]
        )
        localparts = mlist.get_localparts(
            header_fields=["comments-to"],
            per_domain=False,
            return_msg_counts=True,
        )
        localparts = list(map(list, zip(*localparts["comments-to"])))
        assert "3gpp_tsg_sa_wg4_video" in localparts[0]
        assert "ivarga" in localparts[0]
        assert "milan.jelinek" in localparts[0]
        assert set(localparts[1]) == {1, 2, 3, 4, 6, 7}

    def test__get_localpartscount(self, mlist):
        localparts = mlist.get_localpartscount(
            header_fields=["comments-to"],
            per_domain=True,
            per_year=False,
        )
        assert localparts["comments-to"]["list.etsi.org"] == 5
        assert localparts["comments-to"]["usherbrooke.ca"] == 1
        assert localparts["comments-to"]["qti.qualcomm.com"] == 2
        localparts = mlist.get_localpartscount(
            header_fields=["from"],
            per_domain=False,
            per_year=True,
        )
        assert localparts["from"][2020] == 6
        assert localparts["from"][2021] == 9

    def test__get_threadsroot(self, mlist):
        subjects = mlist.get_threadsroot()
        subjects_true = {
            "Draft EVS-8a": 6,
            "IVAS-1 v0.4.0 available in the Inbox": 7,
            "Updated CRs to 26.442/443/444/452 in Inbox": 8,
            "Draft IVAS-8a in Draft folder": 9,
            "Revised IVAS-1 in Draft folder": 10,
            "Draft LS reply to SG12 on P.SUPPL800 & draft IVAS call for labs": 11,
            "Information related to EVS SWG Sessions during SA4#115e meeting": 13,
            "Draft IVAS-8a (IVAS test plan skeleton with Appendix with example test designs)": 14,
            "Information related to EVS SWG Sessions during SA4#114e meeting": 15,
            "IVAS-1 is in the Inbox now": 16,
            "Information for #113e EVS SWG participants": 19,
            "IVAS-7a_v.0.2.0 available in S4-210315": 20,
            "Final IVAS-1 is available in the Inbox": 21,
            "Rev1 of S4-210133 (IVAS-1) is available in the draft folder": 22,
            "FW: [11.5, S4-210129, Block A, 3 Feb 16:00 CET] Update to: Audio mixing of multiple streaming in ITT4RT": 23,
            "Draft revised agenda and report template": 34,
            "FW: [11.5; 1451; 18 Nov 1600 CET] Audio mixing of multiple streaming in ITT4RT - for agreement": 27,
            "Information related to EVS SWG sessions": 28,
            "3GPP SA4#110-e SQ SWG": 29,
            "Update on the Tohru Hand raising Tool": 30,
            "Wednesday meeting": 31,
            "FW: Updated Draft Schedule of MTSI SWG Telco sessions at SA4#110-e": 33,
            "3GPP SA4#110-e EVS SWG": 41,
            "EVS SWG on 28th May: cancelled": 42,
            "GTM Links A/B/C: SA4#109-e SWG Sessions": 44,
            "subscribe": 45,
            "SQA4 Breakout Sessions: =?utf-8?q?Today=E2=80=99s?= link for the online sessions": 46,
            "Hosted: Agenda for SA4#108-e meeting": 47,
            "test mail -": 49,
        }
        for sl in subjects.keys():
            assert subjects[sl] == subjects_true[sl]

    def test__get_threadsrootcount(self, mlist):
        count = mlist.get_threadsrootcount()
        assert count == 29  # as they are all replies

    def test__get_messagescount(self, mlist):
        msgcount = mlist.get_messagescount()
        assert msgcount == 50
        msgcount = mlist.get_messagescount(
            header_fields=["comments-to"],
            per_address_field="domain",
            per_year=False,
        )
        assert msgcount["comments-to"]["list.etsi.org"] == 17
        assert msgcount["comments-to"]["usherbrooke.ca"] == 3
        assert msgcount["comments-to"]["qti.qualcomm.com"] == 8
        msgcount = mlist.get_messagescount(
            header_fields=["from"],
            per_address_field="localpart",
            per_year=True,
        )
        assert msgcount["from"][2020]["milan.jelinek"] == 1
        assert msgcount["from"][2021]["milan.jelinek"] == 3
        assert msgcount["from"][2021]["markus.multrus"] == 2

    def test__get_messagescount_per_timezone(self, mlist):
        msgcount = mlist.get_messagescount_per_timezone()
        assert msgcount["+00:00"] == 38
        assert msgcount["+08:00"] == 6
        assert msgcount["-04:00"] == 3
        assert msgcount["-05:00"] == 1

    def test__get_sender_receiver_dict(self, mlist):
        dic = mlist.get_sender_receiver_dict()
        dic_true = {
            "ericsson.com": {"usherbrooke.ca": 1, "qti.qualcomm.com": 1},
            "usherbrooke.ca": {"ericsson.com": 1, "qti.qualcomm.com": 2},
            "qti.qualcomm.com": {"usherbrooke.ca": 2},
            "philips.com": {"qti.qualcomm.com": 1, "philips.com": 1},
            "iis.fraunhofer.de": {"qti.qualcomm.com": 2},
            "3gpp.org": {"list.etsi.org": 15, "qti.qualcomm.com": 1},
            "samsung.com": {"list.etsi.org": 2},
            "qosound.com": {"qti.qualcomm.com": 1},
            "dolby.com": {},
            "list.etsi.org": {},
        }
        for key1, value1 in dic.items():
            for key2, value2 in value1.items():
                assert dic_true[key1][key2] == value2
