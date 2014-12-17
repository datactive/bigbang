from bigbang.parse import get_date
import urllib2
import urllib
import gzip
import re
import os
import mailbox
import parse
import pandas as pd
from pprint import pprint as pp
import w3crawl

ml_exp = re.compile('/([\w-]*)/$')

gz_exp = re.compile('href="(\d\d\d\d-\w*\.txt\.gz)"')
ietf_ml_exp = re.compile('href="([\d-]+.mail)"')
w3c_archives_exp = re.compile('lists\.w3\.org')

mailing_list_path_expressions = [gz_exp, ietf_ml_exp]


class InvalidURLException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class MissingDataException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def load_data(name,archive_dir="archives",mbox=False):
    """
    Loads the data associated with an archive name, given
    as a string.

    Attempts to open {archives-directory}/NAME.csv as data.

    Failing that, if the the name is a URL, it will try to derive
    the list name from that URL and load the .csv again.

    Failing that, it will collect the data from the web and create the CSV archive.
    """

    if mbox:
        return open_list_archives(name, archive_dir=archive_dir, mbox=True)

    # a first pass at detecting if the string is a URL...
    if not (name.startswith("http://") or name.startswith("https://")):
        path = os.path.join(archive_dir,name + ".csv")

        if os.path.exists(path):
            data = pd.read_csv(path)
            return data
        else:
            print "No data available at %s" % (path)
    else:
        path = os.path.join(archive_dir,get_list_name(name) + ".csv")

        if os.path.exists(path):
            data = pd.read_csv(path)
            return data
        else:
            print "No data found at %s. Attempting to collect data from URL." % (name)
            print "This could take a while."
            return collect_from_url(name,archive_dir=archive_dir)


def collect_from_url(url,archive_dir="archives"):
    url = url.rstrip()
    collect_archive_from_url(url)
    unzip_archive(url)
    data = open_list_archives(url)

    # hard coding the archives directory in too many places
    # need to push this default to a configuration file
    path = os.path.join(archive_dir,get_list_name(url) + ".csv")
    data.to_csv(path, ",")

    return data


def collect_from_file(urls_file):
    for url in open(urls_file):
        collect_from_url(url)


def get_list_name(url):
    import warnings
    try:
        url = url.rstrip()

        return ml_exp.search(url).groups()[0]
    except AttributeError:
        warnings.warn("No mailing list name found at %s" % url)
        return url


def archive_directory(base_dir, list_name):
    arc_dir = os.path.join(base_dir, list_name)
    if not os.path.exists(arc_dir):
        os.makedirs(arc_dir)
    return arc_dir


def collect_archive_from_url(url, archive_dir="archives"):
    list_name = get_list_name(url)
    pp("Getting archive page for %s" % list_name)

    if w3c_archives_exp.search(url):
        return w3crawl.collect_from_url(url, archive_dir)

    response = urllib2.urlopen(url)
    html = response.read()

    results = []
    for exp in mailing_list_path_expressions:
        results.extend(exp.findall(html))

    pp(results)

    # directory for downloaded files
    arc_dir = archive_directory(archive_dir, list_name)

    # download monthly archives
    for res in results:
        result_path = os.path.join(arc_dir, res)
        # this check is redundant with urlretrieve
        if not os.path.isfile(result_path):
            gz_url = url + res
            pp('retrieving %s' % gz_url)
            resp = urllib2.urlopen(gz_url)
            if resp.getcode() == 200:
                print("200 - writing file to %s" % (result_path))
                output = open(result_path, 'wb')
                output.write(resp.read())
                output.close()
            else:
                print("%s error code trying to retrieve %s" %
                      (str(resp.getcode(), gz_url)))


def unzip_archive(url, archive_dir="archives"):
    arc_dir = archive_directory(archive_dir, get_list_name(url))

    gzs = [os.path.join(arc_dir, fn) for fn
           in os.listdir(arc_dir)
           if fn.endswith('.txt.gz')]

    print 'unzipping %d archive files' % (len(gzs))

    for gz in gzs:
        try:
            f = gzip.open(gz, 'rb')
            content = f.read()
            f.close()

            txt_fn = str(gz[:-3])

            f2 = open(txt_fn, 'w')
            f2.write(content)
            f2.close()
        except Exception as e:
            print e

# This works for the names of the files. Order them.
# datetime.datetime.strptime('2000-November',"%Y-%B")

# This doesn't yet work for parsing the dates. Because of %z Bullshit
# datetime.datetime.strptime(arch[0][0].get('Date'),"%a, %d %b %Y %H:%M:%S %z")


def open_list_archives(url, archive_dir="archives", mbox=False):
    """
    Returns a list of all email messages contained in the specified directory.

    The argument *url* here is taken to be the name of a subdirectory
    of the directory specified in argument *archive_dir*.

    This directory is expected to contain files with extensions .txt,
    .mail, or .mbox. These files are all expected to be in mbox format--
    i.e. a series of blocks of text starting with headers (colon-separated
    key-value pairs) followed by an email body.
    """

    messages = None

    if mbox and (os.path.isfile(os.path.join(archive_dir, url))):
        # treat string as the path to a file that is an mbox
        box = mailbox.mbox(os.path.join(archive_dir, url), create=False)
        messages = box.values()
    else:
        # assume string is the path to a directory with many

        list_name = get_list_name(url)
        arc_dir = archive_directory(archive_dir, list_name)

        file_extensions = [".txt", ".mail", ".mbox"]

        txts = [os.path.join(arc_dir, fn) for fn
                in os.listdir(arc_dir)
                if any([fn.endswith(extension) for extension in file_extensions])]

        print 'Opening %d archive files' % (len(txts))
        arch = [mailbox.mbox(txt, create=False).values() for txt in txts]

        messages = [item for sublist in arch for item in sublist]

        if len(messages) == 0:
            raise MissingDataException(
                ("No messages in %s under %s. Did you run the "
                 "collect_mail.py script?") %
                (archive_dir, data))

    return messages_to_dataframe(messages)


def messages_to_dataframe(messages):
    """
    Turn a list of parsed messages into a dataframe of message data,
    indexed by message-id, with column-names from headers.

    """
    # extract data into a list of tuples -- records -- with
    # the Message-ID separated out as an index
    pm = [(m.get('Message-ID'),
           (m.get('From'),
            m.get('Subject'),
            get_date(m),
            m.get('In-Reply-To'),
            m.get('References'),
            m.get_payload()))
          for m in messages if m.get('Message-ID')]

    ids, records = zip(*pm)

    mdf = pd.DataFrame.from_records(list(records),
                                    index=list(ids),
                                    columns=['From',
                                             'Subject',
                                             'Date',
                                             'In-Reply-To',
                                             'References',
                                             'Body'])
    mdf.index.name = 'Message-ID'

    return mdf
