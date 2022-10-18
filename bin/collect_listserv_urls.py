import argparse
import getopt
import logging
import sys
from argparse import RawTextHelpFormatter

from bigbang.config import CONFIG
from bigbang.listserv import ListservArchive

march = ListservArchive.from_url(
    name="3GPP",
    url_root="https://list.etsi.org/scripts/wa.exe",
    url_home="https://list.etsi.org/scripts/wa.exe?HOME",
    login={"username": "nielsto@gmail.com", "password": "BigBang11!"},
    instant_save=False,
    only_mlist_urls=True,
)
textfile = open(
    CONFIG.config_path + "../examples/url_collections/listserv.3GPP.txt",
    "w",
)
for element in march.lists:
    textfile.write(element + "\n")
textfile.close()
