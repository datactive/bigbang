import bigbang.mailman as mailman
from pprint import pprint as pp

ARCHIVE_DIR = "archives"

URLS_FILE = "urls.txt"

for url in open(URLS_FILE):
    url = url.rstrip()
    mailman.collect_from_url(url)
    mailman.unzip_archive(url)
