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
import bigbang.bigbang_io as bio

from bigbang.config import CONFIG

dir_temp = tempfile.gettempdir()
file_temp_mbox = dir_temp + "/listserv.mbox"
file_auth = CONFIG.config_path + "authentication.yaml"
auth_key_mock = {"username": "bla", "password": "bla"}


@pytest.fixture(name="mlist", scope="module")
def get_mailinglist():
    mlist = ListservMailList.from_mbox(
        name="3GPP_TSG_SA_WG4_EVS",
        filepath=CONFIG.test_data_path + "3GPP_mbox/3GPP_TSG_SA_WG4_EVS.mbox",
    )
    return mlist


def test__mlist_to_list_of_mboxMessage(mlist):
    mbox = bio.mlist_to_list_of_mboxMessage(mlist.df, include_body=False)
    msgcount = len(mbox)
    assert msgcount == 50


# def test__mlistdom_to_pandas_dataframe(mlistdom):
# TODO
