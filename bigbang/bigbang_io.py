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
from bigbang.data_types import Message, MailList, MailListDomain

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
logging.basicConfig(
    filename=directory_project + "/listserv.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


def email_to_dict(msg: Message) -> Dict[str, str]:
    """
    Handles data type transformation from `mailbox.mboxMessage` to `Dictionary`.
    """
    dic = {"Body": msg.get_payload()}
    for key, value in msg.items():
        dic[key] = value
    return dic


def email_to_pandas_dataframe(msg: Message) -> pd.DataFrame:
    """
    Handles data type transformation from `mailbox.mboxMessage` to `pandas.DataFrame`.
    """
    return pd.DataFrame(
        email_to_dict(msg),
        index=[msg["Message-ID"]],
    )


def email_to_mbox(msg: Message, filepath: str, mode: str = "w") -> None:
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
    mlist = []
    for msg in list(box.values()):
        _msg = dict(msg)
        if msg.is_multipart():
            # if message has many submessages, only get the top one
            # TODO: it does not detect that
            # https://list.etsi.org/scripts/wa.exe?A2=3GPP_TSG_SA_WG3_LI;6b0e2163.2008B&S=
            # is multipart
            payloads = msg.get_payload()
            _msg["body"] = str(payloads[0].get_payload(decode=True))
        else:
            _msg["body"] = str(msg.get_payload(decode=True))
        mlist.append(_msg)
    mlist = [{k.lower(): v for k, v in msg.items()} for msg in mlist]
    if len(mlist) > 0:
        # TODO: find out why some fields are missing in some messages
        df = pd.DataFrame(mlist)
        # df = utils.clean_addresses(df)
        df = utils.clean_subject(df)
        # df = utils.clean_datetime(df)
        return df
    else:
        return None


def mlist_from_mbox(filepath: str) -> list:
    """
    Reads `mailbox.mboxMessage` objects from .mbox file.
    For a clearer definition on what a mailing list is, see:
    bigbang.ingress.abstract.AbstractList
    """
    box = mailbox.mbox(filepath, create=False)
    return list(box.values())


def mlist_to_dict(
    msgs: MailList,
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
    msgs: MailList,
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


def mlist_to_mbox(msgs: MailList, dir_out: str, filename: str) -> None:
    """
    Saves a List[mailbox.mboxMessage] as .mbox file.
    For a clearer definition on what a mailing list is, see:
    bigbang.ingress.abstract.AbstractList
    """
    # create directory path if it doesn't exist yet
    Path(dir_out).mkdir(parents=True, exist_ok=True)
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


def mlistdom_to_dict(
    mlists: MailListDomain, include_body: bool = True
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
            dic_mlistdom = dic_mlist
            dic_mlistdom["mailing-list"] = [mlist.name] * len(mlist)
        else:
            # add mlist items to mlistdom
            for key, value in dic_mlist.items():
                if key not in dic_mlistdom.keys():
                    dic_mlistdom[key] = [np.nan] * nr_msgs
                dic_mlistdom[key].extend(value)
            # if mlist does not contain items that are in mlistdom
            key_miss = list(set(dic_mlistdom.keys()) - set(dic_mlist.keys()))
            key_miss.remove("mailing-list")
            for key in key_miss:
                dic_mlistdom[key].extend([np.nan] * len(mlist))

            dic_mlistdom["mailing-list"].extend([mlist.name] * len(mlist))
        nr_msgs += len(mlist)
    lengths = [len(value) for value in dic_mlistdom.values()]
    assert all([diff == 0 for diff in np.diff(lengths)])
    return dic_mlistdom


def mlistdom_to_pandas_dataframe(
    mlists: MailListDomain, include_body: bool = True
) -> pd.DataFrame:
    """
    Handles data type transformation from a List[AbstractList] to a
    pandas.DataFrame.
    For a clearer definition on what a mailing archive is, see:
    bigbang.ingress.abstract.AbstractArchive
    """
    df = pd.DataFrame(mlistdom_to_dict(mlists, include_body)).set_index(
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


def mlistdom_to_mbox(mlists: MailListDomain, dir_out: str):
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
