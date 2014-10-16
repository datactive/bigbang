import urllib2
import urllib
import gzip
import re
import os
import mailbox
import parse
from pprint import pprint as pp
import w3crawl

ml_exp = re.compile('/([\w-]*)/$')

gz_exp = re.compile('href="(\d\d\d\d-\w*\.txt\.gz)"')
ietf_ml_exp = re.compile('href="([\d-]+.mail)"')
w3c_archives_exp = re.compile('lists\.w3\.org')

mailing_list_path_expressions = [gz_exp, ietf_ml_exp]


def collect_from_url(url):
    url = url.rstrip()
    collect_archive_from_url(url)
    unzip_archive(url)

def collect_from_file(urls_file):
    for url in open(urls_file):
        collect_archive_from_url(url)

def get_list_name(url):
    url = url.rstrip()

    return ml_exp.search(url).groups()[0]

def archive_directory(base_dir,list_name):
    arc_dir = os.path.join(base_dir,list_name)
    if not os.path.exists(arc_dir):
        os.makedirs(arc_dir)
    return arc_dir


def collect_archive_from_url(url,base_arch_dir="archives"):
    list_name = get_list_name(url)
    pp("Getting archive page for %s" % list_name)
    
    if w3c_archives_exp.search(url):
      return w3crawl.collect_from_url(url, base_arch_dir)

    response = urllib2.urlopen(url)
    html = response.read()

    results = []
    for exp in mailing_list_path_expressions:
      results.extend(exp.findall(html))

    pp(results)

    # directory for downloaded files
    arc_dir = archive_directory(base_arch_dir,list_name)

    # download monthly archives   
    for res in results:
        result_path = os.path.join(arc_dir,res)
        #this check is redundant with urlretrieve
        if not os.path.isfile(result_path):
            gz_url = url + res
            pp('retrieving %s' % gz_url)
            resp = urllib2.urlopen(gz_url)
            if resp.getcode() == 200:
                print("200 - writing file to %s" % (result_path))
                output = open(result_path,'wb')
                output.write(resp.read())
                output.close()
            else:
                print("%s error code trying to retrieve %s" %
                      (str(resp.getcode(),gz_url)))

def unzip_archive(url,base_arc_dir="archives"):
    arc_dir = archive_directory(base_arc_dir,get_list_name(url))

    gzs = [os.path.join(arc_dir,fn) for fn
           in os.listdir(arc_dir)
           if fn.endswith('.txt.gz')]

    print 'unzipping %d archive files' % (len(gzs))

    for gz in gzs:
        try:
            f = gzip.open(gz,'rb')
            content = f.read()
            f.close()

            txt_fn = str(gz[:-3])

            f2 = open(txt_fn,'w')
            f2.write(content)
            f2.close()
        except Exception as e:
            print e

# This works for the names of the files. Order them.
# datetime.datetime.strptime('2000-November',"%Y-%B")

# This doesn't yet work for parsing the dates. Because of %z Bullshit
#datetime.datetime.strptime(arch[0][0].get('Date'),"%a, %d %b %Y %H:%M:%S %z")


def open_list_archives(url,base_arc_dir="archives"):
    """
    Returns a list of all email messages contained in the specified directory.

    The argument *url* here is taken to be the name of a subdirectory
    of the directory specified in argument *base_arc_dir*.

    This directory is expected to contain files with extensions .txt,
    .mail, or .mbox. These files are all expected to be in mbox format--
    i.e. a series of blocks of text starting with headers (colon-separated
    key-value pairs) followed by an email body.
    """
    list_name = get_list_name(url)
    arc_dir = archive_directory(base_arc_dir,list_name)
    
    file_extensions = [".txt", ".mail", ".mbox"]

    txts = [os.path.join(arc_dir,fn) for fn
            in os.listdir(arc_dir)
            if any([fn.endswith(extension) for extension in file_extensions])]

    print 'Opening %d archive files' % (len(txts))
    arch = [mailbox.mbox(txt, create=False).values() for txt in txts]

    messages = [item for sublist in arch for item in sublist]
    return messages


