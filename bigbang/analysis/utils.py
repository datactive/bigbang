from datetime import datetime
import math
import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Union
import mailbox
from mailbox import mboxMessage
from pathlib import Path
import pytz
import numpy as np
import pandas as pd
from bigbang.config import CONFIG


filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
logging.basicConfig(
    filename=directory_project + "/listserv.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


def get_index_of_msgs_with_subject(
    df: pd.DataFrame,
    return_boolmask: bool = False,
) -> np.array:
    boolmask = np.array(
        [
            True if (isinstance(sb, str)) and not pd.isna(sb) else False
            for sb in df.loc[:, "subject"].values
        ],
        dtype="bool",
    )
    index = np.arange(len(boolmask))[boolmask]
    if return_boolmask:
        return boolmask
    else:
        index = df.loc[boolmask].index.values
        return index


def get_index_of_msgs_with_datetime(
    df: pd.DataFrame,
    return_boolmask: bool = False,
) -> np.array:
    cond = lambda x: (
        True
        if (isinstance(x, str) and (len(x) > 10))
        or isinstance(x, datetime)
        and not pd.isna(x)
        else False
    )
    boolmask = np.array([cond(dt) for dt in df.loc[:, "date"].values], dtype="bool")
    if return_boolmask:
        return boolmask
    else:
        index = df.loc[boolmask].index.values
        return index


def clean_addresses(df: pd.DataFrame) -> pd.DataFrame:
    index = np.array(
        [
            True if (isinstance(sb, str)) and not pd.isna(sb) else False
            for sb in df.loc[:, "from"].values
        ],
        dtype="bool",
    )
    # 1 remove multiple white spaces
    # 2 remove leading and trailing white spaces
    # 3 all characters in lower case
    # 4 remove apostrophes and commas as they are not allowed in an atom- or obs-phrase
    df.loc[index, "from"] = [
        re.sub(" +", " ", adrs).strip().lower().replace('"', "").replace(",", "")
        for adrs in df.loc[index, "from"].values
    ]
    index = np.array(
        [
            True if (isinstance(sb, str)) and not pd.isna(sb) else False
            for sb in df.loc[:, "comments-to"].values
        ],
        dtype="bool",
    )
    # 1 remove multiple white spaces
    # 2 remove leading and trailing white spaces
    # 3 all characters in lower case
    # 4 remove apostrophes and commas as they are not allowed in an atom- or obs-phrase
    df.loc[index, "comments-to"] = [
        re.sub(" +", " ", adrs).strip().lower().replace('"', "").replace(",", "")
        for adrs in df.loc[index, "comments-to"].values
    ]
    return df


def clean_subject(df: pd.DataFrame) -> pd.DataFrame:
    index = get_index_of_msgs_with_subject(df)
    # remove leading and trailing apostrophe
    # TODO: this step should not be necessary if it is corrected for in
    # bigbang.listserv.ListservMessageParser
    df.loc[index, "subject"] = [
        re.match(r"^(?:')(.*)(?:')$", sb)[1]
        if re.match(r"^(?:')(.*)(?:')$", sb) is not None
        else sb
        for sb in df.loc[index, "subject"].values
    ]
    # remove multiple spaces in string
    df.loc[index, "subject"] = [
        re.sub(" +", " ", sb) for sb in df.loc[index, "subject"].values
    ]
    return df


def clean_datetime(df: pd.DataFrame) -> pd.DataFrame:
    # filter out messages with unrecognisable datetime
    index = get_index_of_msgs_with_datetime(df)
    # convert data type from string to datetime.datetime object
    df.loc[index, "date"] = [
        datetime.strptime(dt, "%a, %d %b %Y %H:%M:%S %z")
        for dt in df.loc[index, "date"].values
    ]
    return df


email_regex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
domain_regex = r"[@]([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$"


def extract_email(from_field):
    """
    Returns an email address from a string.
    """
    match = re.search(email_regex, from_field)

    if match is not None:
        return match[0].lower()

    else:
        return None


def extract_domain(from_field):
    """
    Returns the domain of an email address from a string.
    """
    match = re.search(email_regex, from_field)

    if match is not None:
        return re.search(domain_regex, match[0])[1]

    else:
        return None


def domain_entropy(domain, froms):
    """
    Compute the entropy of the distribution of counts of email prefixes
    within the given archive.

    Parameters
    ---------------

    domain: string
        An email domain

    froms: pandas.DataFrame
        A pandas.DataFrame with From fields, email address, and domains.
        See the Archive method ``get_froms()``


    Returns
    --------

    entropy: float
    """

    domain_messages = froms[froms["domain"] == domain]

    n_D = domain_messages.shape[0]

    entropy = 0

    emails = domain_messages["email"].unique()

    for em in emails:
        em_messages = domain_messages[domain_messages["email"] == em]
        n_e = em_messages.shape[0]

        p_em = float(n_e) / n_D

        entropy = entropy - p_em * math.log(p_em)

    return entropy


def is_localized(dt):
    """
    Check if a datetime object is localized.
    """
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def localize_to_utc(dt):
    """
    Localize a datetime object to UTC.
    """
    if is_localized(dt):
        # Datetime object is already localized
        return dt.astimezone(pytz.utc)
    else:
        # Assume naive datetime is in UTC
        return pytz.utc.localize(dt)


def parse_date_from_formats(date_str, date_formats):
    """
    Parse a date from a string using one of several possible formats.

    Args:
        date_str (str): The date string to parse.
        date_formats (list): A list of date format strings to attempt parsing.

    Returns:
        datetime object: The parsed datetime object, or None if parsing fails.
    """
    for date_format in date_formats:
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            pass
    return None


def clean_dates(data, start=True):
    if (
        data == "Present"
        or data == "NaN"
        or data == "NaT"
        or issubclass(type(data), type(pd.NaT))
        or data == ""
        or (isinstance(data, float) and np.isnan(data))
    ):
        if start:
            data = datetime.min
        else:
            data = datetime.now()

    if isinstance(data, str):
        data = parse_date_from_formats(data, ["%m/%Y", "%Y"])

        if data is None:
            if start:
                data = datetime.min
            else:
                data = datetime.now()

    data = localize_to_utc(data)

    return data
