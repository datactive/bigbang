import datetime
import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Union
import mailbox
from mailbox import mboxMessage
from pathlib import Path
import numpy as np
import pandas as pd
from config.config import CONFIG

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
        or isinstance(x, datetime.datetime)
        and not pd.isna(x)
        else False
    )
    boolmask = np.array(
        [cond(dt) for dt in df.loc[:, "date"].values], dtype="bool"
    )
    if return_boolmask:
        return boolmask
    else:
        index = df.loc[boolmask].index.values
        return index


def clean_addresses(df: pd.DataFrame) -> pd.DataFrame:
    if "from" in df.columns:
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
            re.sub(" +", " ", adrs)
            .strip()
            .lower()
            .replace('"', "")
            .replace(",", "")
            for adrs in df.loc[index, "from"].values
        ]
    if "comments-to" in df.columns:
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
            re.sub(" +", " ", adrs)
            .strip()
            .lower()
            .replace('"', "")
            .replace(",", "")
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
        datetime.datetime.strptime(dt, "%a, %d %b %Y %H:%M:%S %z")
        for dt in df.loc[index, "date"].values
    ]
    return df
