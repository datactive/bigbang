import bigbang.mailman as mailman
from pprint import pprint as pp

ARCHIVE_DIR = "archives"

URLS_FILE = "urls.txt"

for url in open(URLS_FILE):
    mailman.collect_from_url(url)
