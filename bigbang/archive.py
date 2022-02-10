"""
This module supports the Archive class, a generic
structure representing a collection of archived emails,
typically from a single mailing list.
"""

import datetime
import logging
import mailbox

import numpy as np
import os
import pandas as pd
from pathlib import Path
import pytz

import bigbang.analysis.utils as analysis_utils
import bigbang.ingress.mailman as mailman
from bigbang.parse import get_date, get_text
import bigbang.analysis.process as process
from bigbang.analysis.thread import Node, Thread
from config.config import CONFIG

from . import utils


def load(path):
    data = pd.read_csv(path)
    return Archive(data)


class ArchiveWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class MissingDataException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Archive(object):
    """A representation of a mailing list archive."""

    data = None
    activity = None
    threads = None
    entities = None
    preprocessed = None

    def __init__(self, data, archive_dir=CONFIG.mail_path, mbox=False):
        """
        Initialize an Archive object.

        The behavior of the constructor depends on the type
        of its first argument, data.

        If data is a Pandas DataFrame, it is treated as a representation of
        email messages with columns for Message-ID, From, Date, In-Reply-To,
        References, and Body. The created Archive becomes a wrapper around a
        copy of the input DataFrame.

        If data is a string, then it is interpreted as a path to either a
        single .mbox file (if the optional argument single_file is True) or
        else to a directory of .mbox files (also in .mbox format). Note that
        the file extensions need not be .mbox; frequently they will be .txt.

        Upon initialization, the Archive object drops duplicate entries
        and sorts its member variable *data* by Date.

        Parameters
        ----------
        data : pandas.DataFrame, or str
        archive_dir: str, optional
            Defaults to CONFIG.mail_path
        mbox: bool

        """

        if isinstance(data, pd.core.frame.DataFrame):
            self.data = data.copy()
        elif isinstance(data, str):
            self.data = load_data(data, archive_dir=archive_dir, mbox=mbox)

        try:
            self.data["Date"] = pd.to_datetime(
                self.data["Date"],
                errors="coerce",
                infer_datetime_format=True,
                utc=True,
            )
        except Exception as e:
            logging.error(
                "Error while converting to datetime, despite coerce mode. "
                + f"The error message is: {e}"
            )
            raise ArchiveWarning(
                "Error while converting to datetime, despite coerce mode. "
                + f"The error message is: {e}"
            )

        try:
            self.data.drop_duplicates(inplace=True)
        except Exception as e:
            logging.error(
                "Error while removing duplicate messages, maybe timezone issues?"
                + f"The error message is: {e}",
                exc_info=True,
            )

        # Drops any entries with no Date field.
        # It may be wiser to optionally
        # do interpolation here.
        if self.data["Date"].isnull().any():
            # self.data.dropna(subset=['Date'], inplace=True)
            self.data = self.data[self.data["Date"].notnull()]
            # workaround for https://github.com/pandas-dev/pandas/issues/13407

        # convert any null fields to None -- csv saves these as nan sometimes
        self.data = self.data.where(pd.notnull(self.data), None)
        self.preprocessed = {}

        try:
            # set the index to be the Message-ID column
            self.data.set_index("Message-ID", inplace=True)
        except KeyError:
            # will get KeyError if Message-ID is already index
            pass

        # let's do a pass to try to find bad tzinfo's
        bad_indices = []
        for i, row in self.data.iterrows():
            try:
                row["Date"] < datetime.datetime.now(pytz.utc)
            except Exception as e:
                logging.error(
                    "Error timezone issues while detecting bad rows. "
                    + f"The error message is: {e}",
                    exc_info=True,
                )
                bad_indices.append(i)
                logging.info("Bad timezone on %s", row["Date"])
        if len(bad_indices) > 0:
            # drop those rows that threw an error
            self.data = self.data.drop(bad_indices)
            logging.info("Dropped %d rows", len(bad_indices))

        try:
            self.data.sort_values(by="Date", inplace=True)
        except Exception as e:
            logging.error(
                "Error while sorting, maybe timezone issues?"
                + f" The error message is: {e}",
                exc_info=True,
            )

        if self.data.empty:
            raise MissingDataException(
                "Archive after initial processing is empty. Was data collected properly?"
            )

    def add_affiliation(self, rel_email_affil):
        """
        Uses a DataFrame of email affiliation information and adds it to the archive's data table.

        The email affilation data is expected to have a regular format, with columns:

          - ``email`` - strings, complete email addresses
          - ``affilation`` - strings, names of organizatiosn of affilation
          - ``min_date`` - datetime, the starting date of the affiliation
          - ``max_date`` - datetime,the end date of the affilation.

        Note that this mutates the dataframe in ``self.data`` to add the affiliation data.

        Params
        ------

        rel_email_affil : pandas.DataFrame
        """

        def match_affiliation(row):
            ## TODO: Option to turn off the max or min constraints in case of limited data.
            matches = rel_email_affil[
                (
                    rel_email_affil["email"]
                    == analysis_utils.extract_email(row["From"])
                )
                & (
                    rel_email_affil["min_date"].dt.tz_localize("utc")
                    <= pd.to_datetime(row["Date"])
                )
                & (
                    rel_email_affil["max_date"].dt.tz_localize("utc")
                    >= pd.to_datetime(row["Date"])
                )
            ]
            return (
                matches["affiliation"].values[0]
                if matches.shape[0] > 0
                else None
            )

        self.data["affiliation"] = self.data.apply(match_affiliation, axis=1)

    def resolve_entities(self, inplace=True):
        """Return data with resolved entities.

        Parameters
        ----------
        inplace : bool, default True

        Returns
        -------
        pandas.DataFrame or None
            Returns None if inplace == True

        """
        if self.entities is None:
            if self.activity is None:
                self.get_activity()

            self.entities = process.resolve_sender_entities(self.activity)

        to_replace = []

        value = []

        for e, names in list(self.entities.items()):
            for n in names:
                to_replace.append(n)
                value.append(e)

        data = self.data.replace(
            to_replace=to_replace, value=value, inplace=inplace
        )

        # clear and replace activity with resolved activity
        self.activity = None
        self.get_activity()

        if inplace:
            return self.data
        else:
            return data

    def get_activity(self, resolved=False):
        """
        Get the activity matrix of an Archive.

        Columns of the returned DataFrame are the Senders of emails.
        Rows are indexed by ordinal date.
        Cells are the number of emails sent by each sender on each data.

        If *resolved* is true, then default entity resolution is run on the
        activity matrix before it is returned.
        """
        if self.activity is None:
            self.activity = self.compute_activity(self)

        if resolved:
            self.entities = process.resolve_sender_entities(self.activity)
            eact = utils.repartition_dataframe(self.activity, self.entities)

            return eact

        return self.activity

    def compute_activity(self, clean=True):
        """Return the computed activity."""
        mdf = self.data

        if clean:
            # unnecessary?
            if mdf["Date"].isnull().any():
                mdf = mdf.dropna(subset=["Date"])

            mdf = mdf[
                mdf["Date"] < datetime.datetime.now(pytz.utc)
            ]  # drop messages apparently in the future

        mdf2 = mdf.reindex(columns=["From", "Date"])
        mdf2["Date"] = mdf["Date"].apply(lambda x: x.toordinal())

        activity = (
            mdf2.groupby(["From", "Date"]).size().unstack("From").fillna(0)
        )
        new_date_range = np.arange(mdf2["Date"].min(), mdf2["Date"].max())
        # activity.set_index('Date')
        activity = activity.reindex(new_date_range, fill_value=0)

        return activity

    def get_personal_headers(self, header="From"):
        """
        Returns a dataframe with a row for every message of the archive, containing
        column entries for:

         - The personal header specified. Defaults to "From". Could be "Repy-To".
         - The email address extracted from the From field
         - The domain of the From field

        This dataframe is computed the first time this method is called and then cached.


        Parameters
        ------------

        header: string, default "From"

        Returns
        ----------

        data: pandas.DataFrame
        """
        if header in self.preprocessed:
            return self.preprocessed[header]
        else:
            emails = self.data[header].apply(analysis_utils.extract_email)
            domains = self.data[header].apply(analysis_utils.extract_domain)
            self.preprocessed[header] = pd.concat(
                [self.data[header], emails, domains],
                axis=1,
                keys=[header, "email", "domain"],
            )
            return self.preprocessed[header]

    def get_threads(self, verbose=False):
        """Get threads."""

        if self.threads is not None:
            return self.threads

        df = self.data

        threads = list()
        visited = dict()

        total = df.shape[0]
        c = 0

        for i in df.iterrows():

            if verbose:
                c += 1
                if c % 1000 == 0:
                    logging.info("Processed %d of %d" % (c, total))

            if i[1]["In-Reply-To"] == "None":
                root = Node(i[0], i[1])
                visited[i[0]] = root
                threads.append(Thread(root))
            elif i[1]["In-Reply-To"] not in list(visited.keys()):
                root = Node(i[1]["In-Reply-To"])
                succ = Node(i[0], i[1], root)
                root.add_successor(succ)
                visited[i[1]["In-Reply-To"]] = root
                visited[i[0]] = succ
                threads.append(Thread(root, known_root=False))
            else:
                parent = visited[i[1]["In-Reply-To"]]
                node = Node(i[0], i[1], parent)
                parent.add_successor(node)
                visited[i[0]] = node

        self.threads = threads

        return threads

    def save(self, path, encoding="utf-8"):
        """Save data to csv file."""
        self.data.to_csv(path, ",", encoding=encoding)


def archive_directory(base_dir, list_name):
    """
    Creates a new archive directory for the given list_name unless one already exists.
    Returns the path of the archive directory.
    """
    arc_dir = os.path.join(base_dir, list_name)
    Path(arc_dir).mkdir(parents=True, exist_ok=True)
    return arc_dir


def find_footer(messages, number=1):
    """
    Returns the footer of a DataFrame of emails.

    A footer is a string occurring at the tail of most messages.
    Messages can be a DataFrame or a Series
    """
    if isinstance(messages, pd.DataFrame):
        messages = messages["Body"]

    # sort in lexical order of reverse strings to maximize foot length
    srb = messages.apply(lambda x: None if x is None else x[::-1]).order()
    # srb = df.apply(lambda x: None if x['Body'] is None else x['Body'][::-1],
    #              axis=1).order()
    # begin walking down the series looking for maximal overlap
    counts = {}

    last = None

    def clean_footer(foot):
        return foot.strip()

    for b in srb:
        if last is None:
            last = b
            continue
        elif b is None:
            continue
        else:
            head, i = utils.get_common_head(b, last, delimiter="\n")
            head = clean_footer(head[::-1])
            last = b

            if head in counts:
                counts[head] = counts[head] + 1
            else:
                counts[head] = 1

        last = b

    # reduce candidates that are strictly longer and less frequent
    # than most promising footer candidates
    for n, foot1 in sorted(
        [(v, k) for k, v in list(counts.items())], reverse=True
    ):
        for foot2, m in list(counts.items()):
            if n > m and foot1 in foot2 and len(foot1) > 0:
                counts[foot1] = counts[foot1] + counts[foot2]
                del counts[foot2]

    candidates = sorted(
        [(v, k) for k, v in list(counts.items())], reverse=True
    )

    return candidates[0:number]


def load_data(
    name: str, archive_dir: str = CONFIG.mail_path, mbox: bool = False
):
    """
    Load the data associated with an archive name, given as a string.

    Attempt to open {archives-directory}/NAME.csv as data.

    Failing that, if the the name is a URL, it will try to derive
    the list name from that URL and load the .csv again.

    Parameters
    ----------
    name : str
    archive_dir : str, default CONFIG.mail_path
    mbox : bool, default False
        If true, expects and opens an mbox file at this path

    Returns
    -------
    data : pandas.DataFrame

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
        # TODO: Should "get_list_name" be more general than mailman?
        path = os.path.join(archive_dir, mailman.get_list_name(name) + ".csv")

        if os.path.exists(path):
            data = pd.read_csv(path)
            return data
        else:
            logging.warning(
                "No data found for %s. Check directory name and whether archives have been collected.",
                name,
            )


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


def open_list_archives(
    archive_name: str,
    archive_dir: str = CONFIG.mail_path,
    mbox: bool = False,
) -> pd.DataFrame:
    """
    Return a list of all email messages contained in the specified directory.

    Parameters
    -----------
    archive_name: str
        the name of a subdirectory of the directory specified
        in argument *archive_dir*. This directory is expected to contain
        files with extensions .txt, .mail, or .mbox. These files are all
        expected to be in mbox format-- i.e. a series of blocks of text
        starting with headers (colon-separated key-value pairs) followed by
        an email body.

    archive_dir : str:
        directory containing all messages.

    mbox: bool, default False
        True if there's an mbox file already available for this archive.

    Returns
    --------

    data : pandas.DataFrame

    """
    messages = None

    if mbox and (os.path.isfile(os.path.join(archive_dir, archive_name))):
        # treat string as the path to a file that is an mbox
        box = mailbox.mbox(
            os.path.join(archive_dir, archive_name), create=False
        )
        messages = list(box.values())

    else:
        # assume string is the path to a directory with many
        # TODO: Generalize get_list_name to listserv, w3c?
        list_name = mailman.get_list_name(archive_name)
        arc_dir = archive_directory(archive_dir, list_name)

        file_extensions = [".txt", ".mail", ".mbox"]

        txts = [
            os.path.join(arc_dir, fn)
            for fn in os.listdir(arc_dir)
            if any([fn.endswith(extension) for extension in file_extensions])
        ]

        logging.info(os.listdir(arc_dir))
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
