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
from typing import Dict, List, Optional

import pandas as pd
import yaml
from validator_collection import checkers

from config.config import CONFIG

from . import parse, w3crawl


def from_files(dir_paths: List[str], file_names: List[str]) -> pd.DataFrame:
    """
    Initialise class from LISTSERV formatted mailing list stored locally.

    Args:
        dir_paths:
        file_names:
    """
    # collect paths to all files
    file_paths = []
    for adir, fdsc in zip(dir_paths, file_names):
        file_paths += _get_all_file(adir, fdsc)
    logging.info(f"There are {len(file_paths)} listserv files.")

    first = True
    for file_path in file_paths:
        df = from_file(file_path)
        if first:
            df_tot = df
        else:
            df_tot = df_tot.append(df)

    return df_tot


def from_file(file_path: str) -> pd.DataFrame:
    """
    Args:
        file_path:
    """
    temp_file_path = _create_temporary_file()
    _erase_file_content(temp_file_path)
    _convert_to_mailman(file_path, temp_file_path)
    mbox = mailbox.mbox(temp_file_path, create=False).values()
    df = messages_to_dataframe(mbox)
    return df


def _convert_to_mailman(file_path: str, temp_path: str) -> None:
    """
    Args:
        file_path: Of the original file in LISTERV format.
        temp_path: Of the GNU-Mailman converted file.
    """
    file = open(file_path, "r")
    content = file.readlines()
    # get positions of all Emails in file
    line_nrs_header_start = _get_line_numbers_of_header_starts(content)
    line_nrs_header_end = _get_line_numbers_of_header_ends(
        content, line_nrs_header_start
    )

    # run through all Emails in file and convert each to GNU-Mailman format
    for idx in range(len(line_nrs_header_end)):
        header_dict = _get_header(
            content[line_nrs_header_start[idx] : line_nrs_header_end[idx] + 1],
        )
        _write_header(temp_path, header_dict)
        _write_body(
            temp_path,
            content[line_nrs_header_end[idx] : line_nrs_header_start[idx + 1]],
        )
    file.close()


def _write_body(
    temp_path: str,
    content: list,
) -> None:
    """"""
    f = open(temp_path, "a")
    # write all non-empty line to Email body
    [f.write(line) for line in content if len(line) > 1]
    f.close()


def _get_header(
    content: list,
) -> Dict[str, str]:
    """
    Args:
        content:
    """
    # collect important info from LISTSERV header
    header_dict = {}
    for lnr in range(len(content)):
        line = content[lnr]

        # get header keyword and value
        if re.match(r"\S+:\s+\S+", line):
            key = line.split(":")[0]
            value = line.replace(key + ":", "").lstrip().rstrip("\n")

            # if header-keyword value is split over two lines
            if not re.match(r"\S+:\s+\S+", content[lnr + 1]):
                value += " " + content[lnr + 1].lstrip().rstrip("\n")

            header_dict[key] = value

    # filter out building blocks for GNU-Mailman format
    header_dict["Mm-Date"] = get_date(header_dict["Date"])
    header_dict["Mm-From"] = get_from(header_dict["From"])
    header_dict["Mm-Name"] = get_name(header_dict["From"])
    header_dict["Message-ID"] = create_message_id(
        header_dict["Mm-Date"],
        header_dict["Mm-From"],
    )

    mailman_header_keywords = [
        "Content-Type",
        "MIME-Version",
        "In-Reply-To",
        "From",
        "Subject",
        "Date",
    ]
    for key in mailman_header_keywords:
        if key not in list(header_dict.keys()):
            header_dict[key] = None
    return header_dict


def _write_header(temp_path: str, header_dict: Dict[str, str]) -> None:
    """
    Args:
        temp_path:
        content:
    """
    f = open(temp_path, "a")
    f.write("\n")
    f.write(f"From b'{header_dict['Mm-From']}' {header_dict['Mm-Date']}\n")
    f.write(f"Content-Type: {header_dict['Content-Type']}\n")
    f.write(f"MIME-Version: {header_dict['MIME-Version']}\n")
    f.write(f"In-Reply-To: {header_dict['In-Reply-To']}\n")
    f.write(f"From: {header_dict['Mm-Name']} <b'{header_dict['Mm-From']}'>\n")
    f.write(f"Subject: b'{header_dict['Subject']}\n")
    f.write(f"Message-ID: <{header_dict['Message-ID']}>'\n")
    f.write(f"Date: {header_dict['Date']}'\n")
    f.write("\n")
    f.close()


def get_date(
    line: str,
) -> str:
    line = (" ").join(line.split(" ")[:-1]).lstrip()
    # convert format to local version of date and time
    date_time_obj = datetime.datetime.strptime(line, "%a, %d %b %Y %H:%M:%S")
    return date_time_obj.strftime("%c")


def get_from(
    line: str,
) -> str:
    # get string in between < and >
    email_of_sender = re.findall(r"\<(.*)\>", line)[0]
    return email_of_sender


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


def create_message_id(
    date: str,
    from_address: str,
) -> str:
    message_id = (".").join([date, from_address])
    # remove special characters
    message_id = re.sub(r"[^a-zA-Z0-9]+", "", message_id)
    return message_id


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
            parse.get_date(m),
            str(m.get("In-Reply-To")),
            str(m.get("References")),
            parse.get_text(m),
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


def _get_all_file(
    directory: str,
    file_dsc: str,
) -> List[str]:
    """ Get paths of all files matching file_dsc in directory """
    print("_get_all_file ---->", directory, file_dsc)
    template = f"{directory}{file_dsc}"
    file_paths = glob.glob(template)
    return file_paths


def _create_temporary_file() -> str:
    """
    Create file which stores GNU-Mailman converted version of the LISTSERV file
    """
    temp_dir_path = tempfile.gettempdir()  # get path to /tmp/ folder
    temp_file_path = os.path.join(
        temp_dir_path, "tempcopy"
    )  # create temporary file
    return temp_file_path


def _erase_file_content(file_path: str) -> None:
    f = open(file_path, "w")
    f.write("\n")
    f.close()


def _get_line_numbers_of_header_starts(content: List[str]) -> List[int]:
    """
    Args:
        content:

    Returns:
        [List of line numbers where header starts] + \
        [with additional -1 to get the body of the last Email]
    """
    return [
        line_nr for line_nr, line in enumerate(content) if "=" * 73 in line
    ] + [-1]


def _get_line_numbers_of_header_ends(
    content: List[str],
    line_nrs_header_start: int,
) -> List[int]:
    """
    Args:
        content:
    """
    line_nrs_header_end = []
    for lnr_a in line_nrs_header_start:
        for lnr_b, lheader in enumerate(content[lnr_a:]):
            if len(lheader) <= 1:
                line_nrs_header_end.append(lnr_a + lnr_b)
                break
    return line_nrs_header_end
