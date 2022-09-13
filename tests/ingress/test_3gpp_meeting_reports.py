import os
import tempfile
from pathlib import Path
from unittest import mock
import shutil
import gzip
import requests

import pytest
import yaml

import bigbang
from bigbang.ingress import (
    ThreeGPPWGArchive,
)
from config.config import CONFIG

directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
url_3gppwgarchive = "https://www.3gpp.org/ftp/tsg_sa/WG3_Security"
url_3gppwgmeeting = url_3gppwgarchive +"/TSGS3_01"


class TestThreeGPPWGArchive:
    @pytest.fixture(name="marchive", scope="module")
    def get_mailinglist_from_url(self):
        marchive = ThreeGPPWGArchive.from_url(
            name="TSG_SA",
            url=url_3gppwgarchive,
            select={
                "years": 2018,
                "file_extensions": ["docx", "txt"],
            },
        )
        return marchive

    def test__mailinglist_content(self, marchive):
        assert 1 ==2 
