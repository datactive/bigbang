import urllib2
import urllib
import re
import os
from pprint import pprint as pp

ARCHIVE_DIR = "archives"

URLS_FILE = "urls.txt"

ml_exp = re.compile('/([\w-]*)/$')

gz_exp = re.compile('href="(\d\d\d\d-\w*\.txt\.gz)"')


for url in open(URLS_FILE):

    url = url.rstrip()

    list_name = ml_exp.search(url).groups()[0]
    
    pp("Getting archive page for %s" % list_name)

    response = urllib2.urlopen(url)
    html = response.read()

    results = gz_exp.findall(html)

    pp(results)

    # directory for downloaded files
    arc_dir = os.path.join(ARCHIVE_DIR,list_name)
    if not os.path.exists(arc_dir):
        os.makedirs(arc_dir)

    # download monthly archives   
    for res in results:
        result_path = os.path.join(arc_dir,res)
        if not os.path.isfile(result_path):
            gz_url = url + res
            pp('retrieving %s' % gz_url)
            info = gz = urllib.urlretrieve(gz_url,result_path)
            print info[0].gettype()
