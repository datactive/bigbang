import codecs
import datetime
import fnmatch
import glob
import gzip
import logging
import mailbox
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import warnings
from pprint import pprint as pp
from typing import Dict, List, Optional

import pandas as pd
import yaml
from validator_collection import checkers

from bigbang.parse import get_date
from config.config import CONFIG

from . import parse, w3crawl

ml_exp = re.compile(r"/([\w-]+)/?$")

txt_exp = re.compile(r'href="(\d\d\d\d-\w*\.txt)"')

gz_exp = re.compile(r'href="(\d\d\d\d-\w*\.txt\.gz)"')
ietf_ml_exp = re.compile(r'href="([\d-]+.mail)"')
w3c_archives_exp = re.compile(r"lists\.w3\.org")

mailing_list_path_expressions = [gz_exp, ietf_ml_exp, txt_exp]

PROVENANCE_FILENAME = "provenance.yaml"

file_extensions = ["txt", "mail", "mbox", "LOG"]


class MissingDataException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ListServ:
    def __init__(
        self,
        data: pd.DataFrame,
    ):
        self.data = data

    # @classmethod
    # def from_url(cls, url: str) -> "ListServ": #TODO

    @classmethod
    def from_archives(
        cls,
        archive_dirs: List[str],
        file_dscs: Optional[List[Dict[str, str]]] = None,
        file_regex: Optional[List[str]] = None,
    ) -> "ListServ":
        """
        Initialise class from LISTSERV formatted mailing list stored locally.

        Args:
            archive_dirs: Directory where log files are stored.
            file_dscs: Description of files to load, e.g.:
                {"root": "", "extension": "LOG"}
        """
        file_paths = []
        for adir, fdsc in zip(archive_dirs, file_dscs):
            file_paths += ListServ._get_all_file(adir, fdsc)
        logging.info(f"There are {len(file_paths)} archive files")

        arch = []
        # for file_path in ["/home/christovis/02_AGE/datactive/bigbang/archives/3GPP_TSG_SA_WG2_PROSE_GCSE_LTE/3GPP_TSG_SA_WG2_PROSE_GCSE_LTE.LOG1307C"]:  #file_paths:
        for file_path in file_paths:
            # create temporary copy of file
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, "tempcopy")
            ListServ.listserv_to_mailman(file_path, temp_path)
            arch.append(mailbox.mbox(temp_path, create=False).values())

        messages = [item for sublist in arch for item in sublist]
        return cls(messages_to_dataframe(messages))

    @staticmethod
    def _get_all_file(
        directory: str,
        file_dsc: Dict[str, str],
    ) -> List[str]:
        """ Get paths of all files matching file_dsc in directory """
        template = f"{directory}{file_dsc['root']}*{file_dsc['extension']}*"
        file_paths = glob.glob(template)
        file_paths = [
            file
            for file in file_paths
            if file_dsc["extension"] in file.split(".")[-1]
        ]
        return file_paths

    @staticmethod
    def listserv_to_mailman(
        file_path: str, temp_path: str, save: bool = False
    ) -> None:
        """  """
        f = open(temp_path, "w")
        f.write("\n")
        f.close()

        with open(file_path, "r") as file:
            content = file.readlines()
            line_nrs_header_start = [
                line_nr
                for line_nr, line in enumerate(content)
                if "=" * 73 in line
            ]
            line_nrs_header_end = []
            for lnr_a in line_nrs_header_start:
                for lnr_b, lheader in enumerate(content[lnr_a:]):
                    if len(lheader) <= 1:
                        line_nrs_header_end.append(lnr_a + lnr_b)
                        break

            for idx in range(len(line_nrs_header_start)):
                ListServ.write_header(
                    temp_path,
                    content,
                    line_nrs_header_start[idx],
                    line_nrs_header_end[idx],
                )
                if idx + 1 == len(line_nrs_header_start):
                    lnr_end = -1
                else:
                    lnr_end = line_nrs_header_start[idx + 1]
                ListServ.write_body(
                    temp_path, content, line_nrs_header_end[idx], lnr_end
                )

    @staticmethod
    def write_body(
        temp_path: str,
        content: list,
        line_nr_start: int,
        line_nr_end: int,
    ) -> None:
        f = open(temp_path, "a")
        [
            f.write(line)
            for line in content[line_nr_start:line_nr_end]
            if len(line) > 1
        ]
        f.close()

    @staticmethod
    def write_header(
        temp_path: str,
        content: list,
        line_nr_start: int,
        line_nr_end: int,
    ) -> None:
        header_dict = {}
        for lnr in range(line_nr_start + 1, line_nr_end):
            line = content[lnr]
            if re.match(r"\S+:\s+\S+", line):
                key = line.split(":")[0]
                value = line.replace(key + ":", "").lstrip().rstrip("\n")
                if not re.match(r"\S+:\s+\S+", content[lnr + 1]):
                    value += " " + content[lnr + 1].lstrip().rstrip("\n")
                header_dict[key] = value
        _date = ListServ.get_date(header_dict["Date"])
        _from = ListServ.get_from(header_dict["From"])
        _name = ListServ.get_name(header_dict["From"])
        _message_id = ListServ.create_message_id(_date, _from)

        if "Content-Type" not in list(header_dict.keys()):
            header_dict["Content-Type"] = None
        if "MIME-Version" not in list(header_dict.keys()):
            header_dict["MIME-Version"] = None

        f = open(temp_path, "a")
        f.write("\n")
        f.write(f"From b'{_from}' {_date}\n")
        f.write(f"Content-Type: {header_dict['Content-Type']}\n")
        f.write(f"MIME-Version: {header_dict['MIME-Version']}\n")
        f.write(f"From: {_name} <b'{_from}'>\n")
        f.write(f"Subject: b'{header_dict['Subject']}\n")
        f.write(f"Message-ID: <{_message_id}>'\n")
        f.write(f"Date: {header_dict['Date']}'\n")
        f.write("\n")
        f.close()

    @staticmethod
    def get_date(
        line: str,
    ) -> str:
        line = (" ").join(line.split(" ")[:-1]).lstrip()
        # convert format to local version of date and time
        date_time_obj = datetime.datetime.strptime(
            line, "%a, %d %b %Y %H:%M:%S"
        )
        return date_time_obj.strftime("%c")

    @staticmethod
    def get_from(
        line: str,
    ) -> str:
        # get string in between < and >
        email_of_sender = re.findall(r"\<(.*)\>", line)[0]
        return email_of_sender

    @staticmethod
    def get_name(
        line: str,
    ) -> str:
        # get string in between < and >
        email_of_sender = re.findall(r"\<(.*)\>", line)[0]
        # remove email_of_sender from line
        name = line.replace("<" + email_of_sender + ">", "")
        # remove special characters
        name = re.sub(r"[^a-zA-Z0-9]+", " ", name)
        return name

    @staticmethod
    def create_message_id(
        date: str,
        from_address: str,
    ) -> str:
        message_id = (".").join([date, from_address])
        # remove special characters
        message_id = re.sub(r"[^a-zA-Z0-9]+", "", message_id)
        return message_id


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


def messages_to_dataframe(messages: list) -> pd.DataFrame:
    """
    Turn a list of parsed messages into a dataframe of message data,
    indexed by message-id, with column-names from headers.

    Args:
    Returns:
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
