from bigbang.parse import get_date
import urllib2
import urllib
import gzip
import re
import os
import fnmatch
import mailbox
import parse
import pandas as pd
from pprint import pprint as pp
import w3crawl
import warnings
import logging

ml_exp = re.compile('/([\w-]+)/?$')

txt_exp = re.compile('href="(\d\d\d\d-\w*\.txt)"')

gz_exp = re.compile('href="(\d\d\d\d-\w*\.txt\.gz)"')
ietf_ml_exp = re.compile('href="([\d-]+.mail)"')
w3c_archives_exp = re.compile('lists\.w3\.org')

mailing_list_path_expressions = [gz_exp, ietf_ml_exp,txt_exp]


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


def load_data(name,archive_dir="../archives",mbox=False):
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
            print "No data found at %s. Check if directory name is correct and if you really collected archives!" % (name)
            


def collect_from_url(url,archive_dir="../archives"):
    url = url.rstrip()
    try:
        has_archives = collect_archive_from_url(url, archive_dir)
    except urllib2.HTTPError as e:
        print "HTTP 404 Error: %s" % (url)
        return None

    if has_archives:
        unzip_archive(url)
        data = open_list_archives(url)

        # hard coding the archives directory in too many places
        # need to push this default to a configuration file
        path = os.path.join(archive_dir, get_list_name(url) + ".csv").replace("\\","/")

        try:
            data.to_csv(path, ",", encoding="utf-8")
        except Exception as e:
            print e
            # if encoding doesn't work...don't encode?
            try:
                data.to_csv(path, ",")
            except Exception as e:
                print e
                print "Can't export data. Aborting."
                return None

        return data
    else:
        return None


def collect_from_file(urls_file, archive_dir="../archives"):
    for url in open(urls_file):
        collect_from_url(url, archive_dir)

# gets the 'list name' from a canonical mailman archive url
# does nothing if it's not this kind of url
# it would be better to catch these non-url cases earlier
def get_list_name(url):
    url = url.rstrip()

    if ml_exp.search(url) is not None:
        return ml_exp.search(url).groups()[0]
    else:
        warnings.warn("No mailing list name found at %s" % url)
        return url


def archive_directory(base_dir, list_name):
    arc_dir = os.path.join(base_dir, list_name)
    if not os.path.exists(arc_dir):
        os.makedirs(arc_dir)
    return arc_dir


def collect_archive_from_url(url, archive_dir="../archives"):
    """
    Collects archives (generally tar.gz) files from mailmain
    archive page.

    Returns True if archives were downloaded, False otherwise
    (for example if the page lists no accessible archive files).
    """
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
            gz_url = "/".join([url.strip("/"),res])
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

    # return True if any archives collected, false otherwise
    return len(results) > 0


def unzip_archive(url, archive_dir="../archives"):
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

# x is a String, a Message, or a list of Messages
# The payload of a Message may be a String, a Message, or a list of Messages.
# OR maybe it's never just a Message, but always a list of them.
def recursive_get_payload(x):
    if isinstance(x,str):
        return x
    elif isinstance(x,list):
        #return [recursive_get_payload(y) for y in x]
        return recursive_get_payload(x[0])
    elif isinstance(x,email.message.Message):
        return recursive_get_payload(x.get_payload())
    else:
        print x
        return None

def open_list_archives(url, archive_dir="../archives", mbox=False):
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

        if len(arch) == 0:
            raise MissingDataException(
                ("No messages in %s under %s. Did you run the "
                 "collect_mail.py script?") %
                (archive_dir, list_name))


        messages = [item for sublist in arch for item in sublist]

    return messages_to_dataframe(messages)

def open_activity_summary(url, archive_dir="../archives"):
    """
    Opens the message activity summary for a particular mailing list (as specified by url)
    and returns the dataframe. Returns None if no activity summary export file is found.
    """
    list_name = get_list_name(url)
    arc_dir = archive_directory(archive_dir, list_name)

    activity_csvs = fnmatch.filter(os.listdir(arc_dir), '*-activity.csv')
    if (len(activity_csvs) == 0):
        logging.info('No activity summary found for %s.' % list_name)
        return None
    
    if (len(activity_csvs) > 1):
        logging.info('Multiple possible activity summary files found for %s, using the first one.' % list_name)
    
    activity_csv = activity_csvs[0]
    path = os.path.join(arc_dir, activity_csv)
    activity_frame = pd.read_csv(path, index_col=0, encoding='utf-8')
    return activity_frame

def get_text(msg):
    ## This code for character detection and dealing with exceptions is terrible
    ## It is in need of refactoring badly. - sb
    import chardet
    text = u""
    if msg.is_multipart():
        html = None
        for part in msg.walk():
            if part.get_content_charset() is None:
                charset = chardet.detect(str(part))['encoding']
            else:
                charset = part.get_content_charset()
            if part.get_content_type() == 'text/plain':
                try:
                    text = unicode(part.get_payload(decode=True), str(charset), "ignore")
                except LookupError as e:
                    print "%s unknown encoding in message %s, using UTF-8 instead" % (charset,msg['Message-ID'])
                    charset = "utf-8"
                    text = unicode(part.get_payload(decode=True), str(charset), "ignore")

            if part.get_content_type() == 'text/html':
                try:
                    html = unicode(part.get_payload(decode=True), str(charset), "ignore")
                except LookupError as e:
                    print "%s unknown encoding in message %s, using UTF-8 instead" % (charset,msg['Message-ID'])
                    charset = "utf-8"
                    html = unicode(part.get_payload(decode=True), str(charset), "ignore")

        if text is not None:
            return text.strip()
        else:
            import html2text
            h = html2text.HTML2Text()
            h.encoding = 'utf-8'
            return unicode(h.handle(html))
    else:
        charset = msg.get_content_charset() or 'utf-8'
        try:
            text = unicode(msg.get_payload(), encoding=charset, errors='ignore')
        except LookupError as e:
            print "%s unknown encoding in message %s, using UTF-8 instead" % (charset,msg['Message-ID'])
            charset = "utf-8"
            text = unicode(msg.get_payload(), encoding=charset, errors='ignore')
        return text.strip()

def messages_to_dataframe(messages):
    """
    Turn a list of parsed messages into a dataframe of message data,
    indexed by message-id, with column-names from headers.

    """
    def safe_unicode(t):
        return t and unicode(t, 'utf-8', 'ignore')
    # extract data into a list of tuples -- records -- with
    # the Message-ID separated out as an index
    pm = [(m.get('Message-ID'),
           safe_unicode(m.get('From')),
           safe_unicode(m.get('Subject')),
           get_date(m),
           safe_unicode(m.get('In-Reply-To')),
           safe_unicode(m.get('References')),
           get_text(m))
          for m in messages if m.get('Message-ID')]

    mdf = pd.DataFrame.from_records(list(pm),
                                    index='Message-ID',
                                    columns=['Message-ID', 'From',
                                             'Subject',
                                             'Date',
                                             'In-Reply-To',
                                             'References',
                                             'Body'])
    mdf.index.name = 'Message-ID'

    return mdf
