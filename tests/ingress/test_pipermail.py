import os
import tempfile
from pathlib import Path
from unittest import mock
import shutil

import pytest
import yaml

import bigbang
from bigbang.ingress import (
    PipermailMessageParser,
    PipermailMailList,
)
from config.config import CONFIG

url_mlistdom = "https://mm.icann.org/pipermail/"
url_list = url_mlistdom + "accred-model"


class TestPipermailMailList:
    @pytest.fixture(name="mlist", scope="module")
    def get_mailinglist_from_url(self):
        mlist = PipermailMailList.from_url(
            name="accred-model",
            url=url_list,
            select={
                "years": 2018,
                "fields": "total",
            },
        )
        assert 1 == 2
        return mlist

    def test__get_mailinglist_from_messages(self, mlist):
        #msgs_urls = [
        #    "https://mm.icann.org/pipermail/ssr2-review/2021-October/002465.html",
        #    "https://mm.icann.org/pipermail/ssr2-review/2021-October/002466.html",
        #]
        #mlist = PipermailMailList.from_messages(
        #    name="ssr2-review",
        #    url=url_list,
        #    messages=msgs_urls,
        #)
        assert len(mlist.messages) == 2

    #def test__mailinglist_content(self, mlist):
    #    assert mlist.name == "ssr2-review"
    #    assert mlist.source == url_list
    #    assert len(mlist) == 14
    #    assert (
    #        mlist.messages[0]["Subject"]
    #        == "Re: Test the Web Forward Documentation Update"
    #    )

    #def test__to_dict(self, mlist):
    #    dic = mlist.to_dict()
    #    assert len(list(dic.keys())) == 9
    #    assert len(dic[list(dic.keys())[0]]) == 14
