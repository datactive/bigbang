import datetime
import glob
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

from bigbang.analysis import utils

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
logging.basicConfig(
    filename=directory_project + "/listserv.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


def email_to_dict(msg: mboxMessage) -> Dict[str, str]:
    """
    Handles data type transformation from `mailbox.mboxMessage` to `Dictionary`.
    """
    dic = {"Body": msg.get_payload()}
    for key, value in msg.items():
        dic[key] = value
    return dic


def email_to_pandas_dataframe(msg: mboxMessage) -> pd.DataFrame:
    """
    Handles data type transformation from `mailbox.mboxMessage` to `pandas.DataFrame`.
    """
    return pd.DataFrame(
        email_to_dict(msg),
        index=[msg["Message-ID"]],
    )


def email_to_mbox(msg: mboxMessage, filepath: str, mode: str = "w") -> None:
    """
    Saves `mailbox.mboxMessage` as .mbox file.
    """
    if Path(filepath).is_file():
        Path(filepath).unlink()
    mbox = mailbox.mbox(filepath)
    mbox.lock()
    mbox.add(msg)
    mbox.flush()
    mbox.unlock()


def mlist_from_mbox_to_pandas_dataframe(filepath: str) -> pd.DataFrame:
    """
    Reads `mailbox.mboxMessage` objects from .mbox file and transforms it to a
    `pandas.DataFrame`.
    For a clearer definition on what a mailing list is, see:
    bigbang.ingress.abstract.AbstractList
    """
    box = mailbox.mbox(filepath, create=False)
    mlist = [dict(msg) for msg in list(box.values())]
    # TODO: find out why some fields are missing in some messages
    nr_of_fields = np.array([len(msg.keys()) for msg in mlist])
    nr_of_fields = np.unique(nr_of_fields, return_counts=True)
    df = pd.DataFrame(mlist)
    df = utils.clean_addresses(df)
    df = utils.clean_subject(df)
    df = utils.clean_datetime(df)
    return df


def mlist_from_mbox(filepath: str) -> list:
    """
    Reads `mailbox.mboxMessage` objects from .mbox file.
    For a clearer definition on what a mailing list is, see:
    bigbang.ingress.abstract.AbstractList
    """
    box = mailbox.mbox(filepath, create=False)
    return list(box.values())


def mlist_to_dict(
    msgs: List[mboxMessage],
    include_body: bool = True,
) -> Dict[str, List[str]]:
    """
    Handles data type transformation from a List[mailbox.mboxMessage] to a
    Dictionary.
    For a clearer definition on what a mailing list is, see:
    bigbang.ingress.abstract.AbstractList
    """
    dic = {}
    for idx, msg in enumerate(msgs):
        # if msg["message-id"] != None:  #TODO: why are some 'None'?
        for key, value in msg.items():
            key = key.lower()
            if key not in dic.keys():
                dic[key] = [np.nan] * len(msgs)
            dic[key][idx] = value
    if include_body:
        dic["body"] = [np.nan] * len(msgs)
        for idx, msg in enumerate(msgs):
            # if msg["message-id"] != None:
            dic["body"][idx] = msg.get_payload()
    lengths = [len(value) for value in dic.values()]
    assert all([diff == 0 for diff in np.diff(lengths)])
    return dic


def mlist_to_pandas_dataframe(
    msgs: List[mboxMessage],
    include_body: bool = True,
) -> pd.DataFrame:
    """
    Handles data type transformation from a List[mailbox.mboxMessage] to a
    pandas.DataFrame.
    For a clearer definition on what a mailing list is, see:
    bigbang.ingress.abstract.AbstractList
    """
    dic = mlist_to_dict(msgs, include_body)
    df = pd.DataFrame(dic)
    # filter out messages with unrecognisable datetime
    index = np.array(
        [
            True
            if (isinstance(dt, str)) and (len(dt) > 10) and not pd.isna(dt)
            else False
            for i, dt in enumerate(df["date"])
        ],
        dtype="bool",
    )
    df = df.loc[index, :]
    # convert data type from string to datetime.datetime object
    df.loc[:, "date"].update(
        df.loc[:, "date"].apply(
            lambda x: datetime.datetime.strptime(x, "%a, %d %b %Y %H:%M:%S %z")
        )
    )
    return df


def mlist_to_mbox(
    msgs: List[mboxMessage], dir_out: str, filename: str
) -> None:
    """
    Saves a List[mailbox.mboxMessage] as .mbox file.
    For a clearer definition on what a mailing list is, see:
    bigbang.ingress.abstract.AbstractList
    """
    # create filepath
    filepath = f"{dir_out}/{filename}.mbox"
    # delete file if there is one at the filepath
    if Path(filepath).is_file():
        Path(filepath).unlink()
    mbox = mailbox.mbox(filepath)
    mbox.lock()
    for msg in msgs:
        try:
            mbox.add(msg)
        except Exception as e:
            logger.info(
                f'Add to .mbox error for {msg["Archived-At"]} because, {e}'
            )
    mbox.flush()
    mbox.unlock()
    logger.info(f"The list {filename} is saved at {filepath}.")
    mbox.lock()
    mbox.add(msg)
    mbox.flush()
    mbox.unlock()


def march_to_dict(
    mlists: list, include_body: bool = True
) -> Dict[str, List[str]]:
    """
    Handles data type transformation from a List[AbstractList] to a
    `Dictionary`.
    For a clearer definition on what a mailing archive is, see:
    bigbang.ingress.abstract.AbstractArchive
    """
    nr_msgs = 0
    for ii, mlist in enumerate(mlists):
        dic_mlist = mlist_to_dict(mlist.messages, include_body)
        if ii == 0:
            dic_march = dic_mlist
            dic_march["mailing-list"] = [mlist.name] * len(mlist)
        else:
            # add mlist items to march
            for key, value in dic_mlist.items():
                if key not in dic_march.keys():
                    dic_march[key] = [np.nan] * nr_msgs
                dic_march[key].extend(value)
            # if mlist does not contain items that are in march
            key_miss = list(set(dic_march.keys()) - set(dic_mlist.keys()))
            key_miss.remove("mailing-list")
            for key in key_miss:
                dic_march[key].extend([np.nan] * len(mlist))

            dic_march["mailing-list"].extend([mlist.name] * len(mlist))
        nr_msgs += len(mlist)
    lengths = [len(value) for value in dic_march.values()]
    assert all([diff == 0 for diff in np.diff(lengths)])
    return dic_march


def march_to_pandas_dataframe(
    mlists: list, include_body: bool = True
) -> pd.DataFrame:
    """
    Handles data type transformation from a List[AbstractList] to a
    pandas.DataFrame.
    For a clearer definition on what a mailing archive is, see:
    bigbang.ingress.abstract.AbstractArchive
    """
    df = pd.DataFrame(march_to_dict(mlists, include_body)).set_index(
        "message-id"
    )
    # get index of date-times
    index = np.array(
        [
            True
            if (isinstance(dt, str)) and (len(dt) > 10) and not pd.isna(dt)
            else False
            for i, dt in enumerate(df["date"])
        ],
        dtype="bool",
    )
    # convert data type from string to datetime.datetime object
    df.loc[index, "date"].update(
        df.loc[index, "date"].apply(
            lambda x: datetime.datetime.strptime(x, "%a, %d %b %Y %H:%M:%S %z")
        )
    )
    return df


def march_to_mbox(mlists: list, dir_out: str):
    """
    Saves a List[AbstractList] as .mbox file.
    For a clearer definition on what a mailing archive is, see:
    bigbang.ingress.abstract.AbstractArchive
    """
    for mlist in mlists:
        mlist.to_mbox(dir_out)


def get_paths_to_files_in_directory(
    directory: str, file_dsc: str = "*"
) -> List[str]:
    """Get paths of all files matching file_dsc in directory"""
    template = f"{directory}{file_dsc}"
    file_paths = glob.glob(template)
    return file_paths


def get_paths_to_dirs_in_directory(
    directory: str, folder_dsc: str = "*"
) -> List[str]:
    """Get paths of all directories matching file_dsc in directory"""
    template = f"{directory}{folder_dsc}"
    dir_paths = glob.glob(template)
    # normalize directory paths
    dir_paths = [dir_path + "/" for dir_path in dir_paths]
    return dir_paths
