import os
import tempfile
from pathlib import Path
from unittest import mock
from unittest import TestCase

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
from bigbang.analysis.listserv import ListservArchive
from bigbang.analysis.listserv import ListservList

from config.config import CONFIG

dir_temp = tempfile.gettempdir()
file_temp_mbox = dir_temp + "/listserv.mbox"
file_auth = CONFIG.config_path + "authentication.yaml"
auth_key_mock = {"username": "bla", "password": "bla"}

@pytest.fixture(name="mlist", scope="module")
def get_mailinglist():
    mlist = ListservList.from_mbox(
        name="3GPP_TSG_SA_WG4_EVS",
        filepath=CONFIG.test_data_path + "3GPP_mbox/3GPP_TSG_SA_WG4_EVS.mbox",
    )
    return mlist

@pytest.fixture(name="march", scope="module")
def get_mailingarchive():
    march = ListservArchive.from_mbox(
        name="3GPP",
        directorypath=CONFIG.test_data_path + "3GPP_mbox/",
        filedsc="3GPP_TSG_*",
    )
    march.df = march.df.dropna()
    return march


class TestListservList:
    def test__to_percentage(self):
        abso = np.array([1, 3])
        perc = ListservList.to_percentage(abso)
        np.testing.assert_array_equal(perc, np.array([0.25, 0.75]))

    def test__get_name_localpart_domain(self):
        addr = '"Gabin, Frederic" <Frederic.Gabin@DOLBY.COM>'
        name, localpart, domain = ListservList.get_name_localpart_domain(addr)
        assert name == "Gabin, Frederic"
        assert localpart == "Frederic.Gabin"
        assert domain == "DOLBY.COM"

    def test__get_messagecount_per_domain(self, mlist):
        dic_msg = mlist.get_messagecount_per_domain(
            percentage=True, contract=0.1
        )
        dic_msg_true = {
            'QOSOUND.COM': 0.12,
            'QTI.QUALCOMM.COM': 0.26,
            '3GPP.ORG': 0.32,
            'Others': 0.3,
        }
        for key in dic_msg.keys():
            assert dic_msg_true[key] == dic_msg[key]

    def test__get_localpart_per_domain(self, mlist):
        dic_mem = mlist.get_localpart_per_domain()
        dic_mem_true = {
            'ERICSSON.COM': ['tomas.toftgard'],
            'USHERBROOKE.CA': ['Milan.Jelinek'],
            'QTI.QUALCOMM.COM': ['ivarga', 'nleung'],
            'QOSOUND.COM': ['hs'],
            'IIS.FRAUNHOFER.DE': ['stefan.doehla', 'markus.multrus'],
            'DOLBY.COM': ['Stefan.Bruhn'],
            'PHILIPS.COM': ['marek.szczerba'],
            '3GPP.ORG': ['Jayeeta.Saha'],
            'SAMSUNG.COM': ['kyunghun.jung'],
        }
        for key in dic_mem.keys():
            for localpart in dic_mem[key]:
                assert localpart in dic_mem_true[key]

    def test__get_localpartcount_per_domain(self, mlist):
        dic_lps = mlist.get_localpartcount_per_domain(
            percentage=True, contract=0.1
        )
        dic_lps_true = {
            'QTI.QUALCOMM.COM': 0.18181818181818182,
            'IIS.FRAUNHOFER.DE': 0.18181818181818182,
            'Others': 0.6363636363636365,
        }
        for key in dic_lps.keys():
            np.testing.assert_almost_equal(
                dic_lps_true[key], dic_lps[key], decimal=7,
            )

    def test__get_sender_receiver_dictionary(self, mlist):
        dic = mlist.get_sender_receiver_dictionary()
        dic_true = {
            'ERICSSON.COM': {'USherbrooke.ca': 1, 'QTI.QUALCOMM.COM': 1},
            'USHERBROOKE.CA': {'ERICSSON.COM': 1, 'qti.qualcomm.com': 1, 'QTI.QUALCOMM.COM': 1},
            'QTI.QUALCOMM.COM': {'USherbrooke.ca': 2},
            'PHILIPS.COM': {'QTI.QUALCOMM.COM': 1, 'philips.com': 1},
            'QOSOUND.COM': {'qti.qualcomm.com': 1},
            'IIS.FRAUNHOFER.DE': {'QTI.QUALCOMM.COM': 2},
            '3GPP.ORG': {'list.etsi.org': 15, 'QTI.QUALCOMM.COM': 1},
            'SAMSUNG.COM': {'LIST.ETSI.ORG': 2},
        }
        for key1, value1 in dic.items():
            for key2, value2 in value1.items():
                assert dic_true[key1][key2] == value2


class TestListservArchive:
    def test__get_mlistscount_per_institution(self, march):
        dic = ListservArchive.get_mlistscount_per_institution(march)
        dic_true = {
            'QTI.QUALCOMM.COM': 2,
            'USHERBROOKE.CA': 1,
            '3GPP.ORG': 1,
            'IIS.FRAUNHOFER.DE': 1,
            'SAMSUNG.COM': 1,
            'ERICSSON.COM': 1,
            'KEYSIGHT.COM': 1,
            'VIVO.COM': 1,
            'PHILIPS.COM': 1,
            'SPIRENT.COM': 1,
            'MEDIATEK.COM': 1,
            'APPLE.COM': 1,
        }
        for key in dic.keys():
            assert dic[key] == dic_true[key]
