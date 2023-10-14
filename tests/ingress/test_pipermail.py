import os
import tempfile
from pathlib import Path
from unittest import mock
import shutil
import gzip
import requests

import pytest
import yaml

from bigbang.ingress import (
    PipermailMessageParser,
    PipermailMailList,
)
from bigbang.config import CONFIG

"""
Disabling test until it can be fixed.
See issue: #608


directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
url_mlistdom = "https://mm.icann.org/pipermail/"
url_list = url_mlistdom + "accred-model"


class TestPipermailMessageParser:
    @pytest.fixture(name="msg", scope="module")
    def get_message(self):
        file = requests.get(
            "https://mm.icann.org/pipermail/accred-model/2018-August.txt.gz",
            verify=os.path.join(CONFIG.config_path, "icann_certificate.pem"),
        )
        fcontent = gzip.decompress(file.content).decode("utf-8")
        fcontent = fcontent.split("\n")
        msg_parser = PipermailMessageParser(website=False)
        msg = msg_parser.from_pipermail_file(
            list_name="accred-model",
            fcontent=fcontent,
            header_end_line_nr=12,
            fields="total",
        )
        return msg

    def test__message_content(self, msg):
        firstline = msg.get_payload().split("=")[0]
        assert "Theo, hope you are well." in firstline
        assert len(firstline) == 635
        assert msg["subject"] == "[Accred-Model] Codes of conduct"
        assert msg["from"] == "jonathan.matkowsky@riskiq.net"
        assert msg["to"] is None
        assert msg["date"] == "Wed, 01 Aug 2018 13:29:58 +0300"
        assert msg["Content-Type"] == 'text/plain; charset="utf-8"'
        assert msg["Archived-At"] == "<accred-model_line_nr_1>"

    def test__to_dict(self, msg):
        dic = PipermailMessageParser.to_dict(msg)
        assert len(list(dic.keys())) == 11


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
        return mlist

    def test__mailinglist_content(self, mlist):
        assert mlist.name == "accred-model"
        assert mlist.source == url_list
        # On 13/09/22 the mailing list contained 175 Emails.
        assert len(mlist) >= 175
        subjects = [msg["subject"] for msg in mlist.messages]
        assert "[Accred-Model] Codes of conduct" in subjects

    def test__to_dict(self, mlist):
        dic = mlist.to_dict()
        # On 13/09/22 the mailing list had 11 (header fields + body).
        assert len(list(dic.keys())) == 11
        # On 13/09/22 the mailing list contained 175 Emails.
        assert len(dic[list(dic.keys())[0]]) >= 175

"""
