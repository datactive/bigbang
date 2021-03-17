import codecs
import datetime
import fnmatch
import gzip
import logging
import mailbox
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import warnings
from pprint import pprint as pp

import pandas as pd
import yaml
from validator_collection import checkers

from bigbang.parse import get_date
from config.config import CONFIG

from . import listserv, parse, w3crawl

ml_exp = re.compile(r"/([\w-]+)/?$")
txt_exp = re.compile(r'href="(\d\d\d\d-\w*\.txt)"')
gz_exp = re.compile(r'href="(\d\d\d\d-\w*\.txt\.gz)"')
ietf_ml_exp = re.compile(r'href="([\d-]+.mail)"')
w3c_archives_exp = re.compile(r"lists\.w3\.org")
listserv_archives_exp = re.compile(r"list\.etsi\.org")

mailing_list_path_expressions = [gz_exp, ietf_ml_exp, txt_exp]

PROVENANCE_FILENAME = "provenance.yaml"


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


def load_data(
    name: str, archive_dir: str = CONFIG.mail_path, mbox: bool = False
):
    """
    Load the data associated with an archive name, given as a string.

    Attempt to open {archives-directory}/NAME.csv as data.

    Failing that, if the the name is a URL, it will try to derive
    the list name from that URL and load the .csv again.

    Args:
        name: archive name
        archive_dir: archive directory path
        mbox:
    """

    if mbox:
        return open_list_archives(name, archive_dir=archive_dir, mbox=True)

    # a first pass at detecting if the string is a URL...
    if not (name.startswith("http://") or name.startswith("https://")):
        path = os.path.join(archive_dir, name + ".csv")

        if os.path.exists(path):
            data = pd.read_csv(path)
            return data
        else:
            logging.warning("No data available at %s", path)
    else:
        path = os.path.join(archive_dir, get_list_name(name) + ".csv")

        if os.path.exists(path):
            data = pd.read_csv(path)
            return data
        else:
            logging.warning(
                "No data found for %s. Check directory name and whether archives have been collected.",
                name,
            )


def collect_from_url(
    url: str, archive_dir: str = CONFIG.mail_path, notes=None
):
    """Collect data from a given url."""

    url = url.rstrip()
    try:
        has_archives = collect_archive_from_url(
            url, archive_dir=archive_dir, notes=notes
        )
    except urllib.error.HTTPError:
        logging.exception("HTTP Error in collecting archive: %s", url)
        return None

    if has_archives:
        unzip_archive(url)
        try:
            data = open_list_archives(url)
        except MissingDataException as e:  # don't strictly need to open the archives during the collection process, so catch the Exception and return
            print(e)
            return None

        # hard coding the archives directory in too many places
        # need to push this default to a configuration file
        path = os.path.join(archive_dir, get_list_name(url) + ".csv").replace(
            "\\", "/"
        )

        try:
            data.to_csv(path, ",", encoding="utf-8")
        except Exception as e:
            print(e)
            # if encoding doesn't work...don't encode? ----better not not encode !!
            # try:
            #     data.to_csv(path, ",")
            # except Exception as e:
            #     print e
            #     print "Can't export data. Aborting."
            #     return None

        return data
    else:
        return None


def urls_to_collect(urls_file: str):
    """Collect urls given urls in a file."""
    urls = []
    for url in open(urls_file):
        url = url.strip()
        if url.startswith("#"):  # comment lines should be ignored
            continue
        if len(url) == 0:  # ignore empty lines
            continue
        if checkers.is_url(url) is not True:
            logging.warning("invalid url: %s" % url)
            continue
        urls.append(url)
    return urls


def collect_from_file(
    urls_file: str,
    archive_dir: str = CONFIG.mail_path,
    notes=None,
):
    """Collect urls from a file."""
    urls = urls_to_collect(urls_file)
    for url in urls:
        collect_from_url(url, archive_dir=archive_dir, notes=notes)


def get_list_name(url):
    """
    Return the 'list name' from a canonical mailman archive url.

    Otherwise return the same URL.
    """
    # TODO: it would be better to catch these non-url cases earlier
    url = url.rstrip()

    if ml_exp.search(url) is not None:
        return ml_exp.search(url).groups()[0]
    else:
        warnings.warn("No mailing list name found at %s" % url)
        return url


def normalize_archives_url(url):
    """
    Normalize url.

    will try to infer, find or guess the most useful archives URL, given a URL.

    Return normalized URL, or the original URL if no improvement is found.
    """
    # change new IETF mailarchive URLs to older, still available text .mail archives
    new_ietf_exp = re.compile(
        "https://mailarchive\\.ietf\\.org/arch/search/"
        "\\?email_list=(?P<list_name>[\\w-]+)"
    )
    ietf_text_archives = (
        r"https://www.ietf.org/mail-archive/text/\g<list_name>/"
    )
    new_ietf_browse_exp = re.compile(
        r"https://mailarchive.ietf.org/arch/browse/(?P<list_name>[\w-]+)/?"
    )

    match = new_ietf_exp.match(url)
    if match:
        return re.sub(new_ietf_exp, ietf_text_archives, url)

    match = new_ietf_browse_exp.match(url)
    if match:
        return re.sub(new_ietf_browse_exp, ietf_text_archives, url)

    return url  # if no other change found, return the original URL


def archive_directory(base_dir, list_name):
    """Archive a directory."""
    arc_dir = os.path.join(base_dir, list_name)
    if not os.path.exists(arc_dir):
        os.makedirs(arc_dir)
    return arc_dir


def populate_provenance(directory, list_name, list_url, notes=None):
    """Create a provenance metadata file for current mailing list collection."""
    provenance = {
        "list": {
            "list_name": list_name,
            "list_url": list_url,
        },
        "date_collected": str(datetime.date.today()),  # uses ISO-8601
        "complete": False,
        "code_version": {
            "long_hash": subprocess.check_output(
                ["git", "rev-parse", "HEAD"]
            ).strip(),
            "description": subprocess.check_output(
                ["git", "describe", "--long", "--always", "--all"]
            ).strip()
            # 'version': '' #TODO: programmatically access BigBang version number, see #288
        },
    }
    if notes:
        provenance["notes"] = notes

    file_path = os.path.join(directory, PROVENANCE_FILENAME)
    if os.path.isfile(file_path):  # a provenance file already exists
        pass  # skip for now
    else:
        file_handle = open(file_path, "w")
        yaml.dump(provenance, file_handle)
        logging.info("Created provenance file for %s" % (list_name))
        file_handle.close()


def access_provenance(directory):
    """
    Return an object with provenance information located in the given directory,
    or None if no provenance was found.
    """
    file_path = os.path.join(directory, PROVENANCE_FILENAME)
    if os.path.isfile(file_path):  # a provenance file already exists
        file_handle = open(file_path, "r")
        provenance = yaml.load(file_handle)
        return provenance
    return None


def update_provenance(directory, provenance):
    """Update provenance file with given object."""
    file_path = os.path.join(directory, PROVENANCE_FILENAME)
    file_handle = open(file_path, "w")
    yaml.dump(provenance, file_handle)
    logging.info("Updated provenance file in %s", directory)
    file_handle.close()


def collect_archive_from_url(url, archive_dir=CONFIG.mail_path, notes=None):
    """
    Collect archives (generally tar.gz) files from mailmain archive page.

    Return True if archives were downloaded, False otherwise
    (for example if the page lists no accessible archive files).
    """
    list_name = get_list_name(url)
    logging.info("Getting archive page for %s", list_name)

    if w3c_archives_exp.search(url):
        return w3crawl.collect_from_url(url, archive_dir, notes=notes)
    elif listserv_archives_exp.search(url):
        listserv.ListservArchive.from_url(
            name="3GPP",
            url_root=url,
            url_home=url + "HOME",
            instant_dump=True,
        )

    response = urllib.request.urlopen(url)
    html = codecs.decode(response.read())

    results = []
    for exp in mailing_list_path_expressions:
        results.extend(exp.findall(html))

    pp(results)

    # directory for downloaded files
    arc_dir = archive_directory(archive_dir, list_name)

    populate_provenance(
        directory=arc_dir, list_name=list_name, list_url=url, notes=notes
    )

    encountered_error = False
    # download monthly archives
    for res in results:
        result_path = os.path.join(arc_dir, res)
        # this check is redundant with urlretrieve
        if not os.path.isfile(result_path):
            gz_url = "/".join([url.strip("/"), res])
            logging.info("retrieving %s", gz_url)
            resp = urllib.request.urlopen(gz_url)
            if resp.getcode() == 200:
                logging.info("200 - writing file to %s", result_path)
                output = open(result_path, "wb")
                output.write(resp.read())
                output.close()
            else:
                logging.warning(
                    "%s error code trying to retrieve %s"
                    % (str(resp.getcode(), gz_url))
                )
                encountered_error = True

    if (
        not encountered_error
    ):  # mark that all available archives were collected
        provenance = access_provenance(arc_dir)
        provenance["complete"] = True
        update_provenance(arc_dir, provenance)

    # return True if any archives collected, false otherwise
    return len(results) > 0


def unzip_archive(url, archive_dir=CONFIG.mail_path):
    """Unzip archive files."""
    arc_dir = archive_directory(archive_dir, get_list_name(url))

    gzs = [
        os.path.join(arc_dir, fn)
        for fn in os.listdir(arc_dir)
        if fn.endswith(".txt.gz")
    ]

    logging.info("Unzipping %d archive files", len(gzs))

    for gz in gzs:
        try:
            f = gzip.open(gz, "rb")
            content = codecs.decode(f.read())
            f.close()

            txt_fn = str(gz[:-3])

            f2 = open(txt_fn, "w")
            f2.write(content)
            f2.close()
        except Exception as e:
            print(e)


# This works for the names of the files. Order them.
# datetime.datetime.strptime('2000-November',"%Y-%B")

# This doesn't yet work for parsing the dates. Because of %z Bullshit
# datetime.datetime.strptime(arch[0][0].get('Date'),"%a, %d %b %Y %H:%M:%S %z")

# x is a String, a Message, or a list of Messages
# The payload of a Message may be a String, a Message, or a list of Messages.
# OR maybe it's never just a Message, but always a list of them.
def recursive_get_payload(x):
    """Get payloads recursively."""
    if isinstance(x, str):
        return x
    elif isinstance(x, list):
        # return [recursive_get_payload(y) for y in x]
        return recursive_get_payload(x[0])
    # TODO: define 'email'
    # elif isinstance(x, email.message.Message):
    #    return recursive_get_payload(x.get_payload())
    else:
        print(x)
        return None


def open_list_archives(
    url: str,
    archive_dir: str = CONFIG.mail_path,
    mbox: bool = False,
) -> pd.DataFrame:
    """
    Return a list of all email messages contained in the specified directory.

    TODO: this argument should be re-named. sometimes it's being called with
        actual URLs, other times with subdirectory names, leading to spurious
        warnings in various places.

    Args:
        url: the name of a subdirectory of the directory specified
            in argument *archive_dir*. This directory is expected to contain
            files with extensions .txt, .mail, or .mbox. These files are all
            expected to be in mbox format-- i.e. a series of blocks of text
            starting with headers (colon-separated key-value pairs) followed by
            an email body.
        archive_dir: directory containing all messages.

    Returns:
    """
    if (url is None) and (archive_dir is None):
        raise ValueError("Either `url` or `archive_dir` must be given.")

    messages = None

    if mbox and (os.path.isfile(os.path.join(archive_dir, url))):
        # treat string as the path to a file that is an mbox
        box = mailbox.mbox(os.path.join(archive_dir, url), create=False)
        messages = list(box.values())

    else:
        # assume string is the path to a directory with many
        list_name = get_list_name(url)
        arc_dir = archive_directory(archive_dir, list_name)

        file_extensions = [".txt", ".mail", ".mbox"]

        txts = [
            os.path.join(arc_dir, fn)
            for fn in os.listdir(arc_dir)
            if any([fn.endswith(extension) for extension in file_extensions])
        ]

        logging.info("Opening %d archive files", len(txts))

        def mbox_reader(stream):
            """Read a non-ascii message from mailbox"""
            data = stream.read()
            text = data.decode(encoding="utf-8", errors="replace")
            return mailbox.mboxMessage(text)

        arch = [
            mailbox.mbox(txt, factory=mbox_reader, create=False).values()
            for txt in txts
        ]

        if len(arch) == 0:
            raise MissingDataException(
                (
                    "No messages in %s under %s. Did you run the "
                    "collect_mail.py script?"
                )
                % (archive_dir, list_name)
            )

        messages = [item for sublist in arch for item in sublist]

    return messages_to_dataframe(messages)


def open_activity_summary(url, archive_dir=CONFIG.mail_path):
    """
    Open the message activity summary for a particular mailing list (as specified by url).

    Return the dataframe, or return None if no activity summary export file is found.
    """
    list_name = get_list_name(url)
    arc_dir = archive_directory(archive_dir, list_name)

    activity_csvs = fnmatch.filter(os.listdir(arc_dir), "*-activity.csv")
    if len(activity_csvs) == 0:
        logging.info("No activity summary found for %s." % list_name)
        return None

    if len(activity_csvs) > 1:
        logging.info(
            "Multiple possible activity summary files found for %s, using the first one."
            % list_name
        )

    activity_csv = activity_csvs[0]
    path = os.path.join(arc_dir, activity_csv)
    activity_frame = pd.read_csv(path, index_col=0, encoding="utf-8")
    return activity_frame


def get_text(msg):
    """Get text from a message."""
    ## This code for character detection and dealing with exceptions is terrible
    ## It is in need of refactoring badly. - sb
    import chardet

    text = ""
    if msg.is_multipart():
        html = None
        for part in msg.walk():
            charset = part.get_content_charset()
            if part.get_content_type() == "text/plain":
                try:
                    text = str(
                        part.get_payload(decode=True), str(charset), "ignore"
                    )
                except LookupError:
                    logging.debug(
                        "Unknown encoding %s in message %s. Will use UTF-8 instead.",
                        charset,
                        msg["Message-ID"],
                    )
                    charset = "utf-8"
                    text = str(
                        part.get_payload(decode=True), str(charset), "ignore"
                    )
            if part.get_content_type() == "text/html":
                try:
                    html = str(
                        part.get_payload(decode=True), str(charset), "ignore"
                    )
                except LookupError:
                    logging.debug(
                        "Unknown encoding %s in message %s. Will use UTF-8 instead.",
                        charset,
                        msg["Message-ID"],
                    )
                    charset = "utf-8"
                    html = str(
                        part.get_payload(decode=True), str(charset), "ignore"
                    )

        if text is not None:
            return text.strip()
        else:
            import html2text

            h = html2text.HTML2Text()
            h.encoding = "utf-8"
            return str(h.handle(html))
    else:
        charset = msg.get_content_charset() or "utf-8"
        if charset != "utf-8":
            logging.debug("charset is %s" % (charset))
        text = msg.get_payload()
        return text.strip()


def messages_to_dataframe(messages):
    """
    Turn a list of parsed messages into a dataframe of message data,
    indexed by message-id, with column-names from headers.
    """
    # extract data into a list of tuples -- records -- with
    # the Message-ID separated out as an index
    # valid_messages = [m for m in messages if m.get()

    pm = [
        (
            m.get("Message-ID"),
            str(m.get("From")).replace("\\", " "),
            str(m.get("Subject")),
            get_date(m),
            str(m.get("In-Reply-To")),
            str(m.get("References")),
            get_text(m),
        )
        for m in messages
        if m.get("From")
    ]

    mdf = pd.DataFrame.from_records(
        list(pm),
        index="Message-ID",
        columns=[
            "Message-ID",
            "From",
            "Subject",
            "Date",
            "In-Reply-To",
            "References",
            "Body",
        ],
    )
    mdf.index.name = "Message-ID"

    return mdf
