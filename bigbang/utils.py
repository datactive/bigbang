"""
Miscellaneous utility functions used in other modules.
"""
import os
import time
import logging
import glob
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from bs4 import BeautifulSoup
import requests

import networkx as nx
import pandas as pd

from config.config import CONFIG

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
logging.basicConfig(
    filename=directory_project + "/scraping.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)


def get_website_content(
    url: str,
    session: Optional[requests.Session] = None,
) -> Union[str, BeautifulSoup]:
    """
    Get HTML code from website

    Note
    ----
    Servers don't like it when one is sending too many requests from same
    ip address in short period of time. Therefore we need to:
        a) catch 'requests.exceptions.RequestException' errors
            (includes all possible errors to be on the safe side),
        b) safe intermediate results,
        c) continue where we left off at a later stage.
    """
    # TODO: include option to change BeautifulSoup args
    try:
        if session is None:
            sauce = requests.get(url)
            assert sauce.status_code == 200
            soup = BeautifulSoup(sauce.content, "html.parser")
        else:
            sauce = session.get(url)
            soup = BeautifulSoup(sauce.text, "html.parser")
        return soup
    except requests.exceptions.RequestException as e:
        if "A2=" in url:
            # if URL of mboxMessage
            logger.info(f"{e} for {url}.")
            return "RequestException"
        else:
            SystemExit()


def set_website_preference_for_header(
    url_pref: str,
    session: requests.Session,
) -> requests.Session:
    """
    Set the 'Email Headers' of the 'Archive Preferences' for the auth session
    to 'Show All Headers'. Otherwise only a restricted list of header fields is
    shown.
    """
    url_archpref = url_pref + "&TAB=2"
    payload = {
        "Email Headers": "b",
    }
    session.post(url_archpref, data=payload)
    return session


def get_auth_session(
    url_login: str, username: str, password: str
) -> requests.Session:
    """
    Create AuthSession.

    There are three ways to create an AuthSession:
        - parse username & password directly into method
        - create a /bigbang/config/authentication.yaml file that contains keys
        - type then into terminal when the method 'get_login_from_terminal'
            is raised
    """
    if os.path.isfile(filepath_auth):
        # read from /config/authentication.yaml
        with open(filepath_auth, "r") as stream:
            auth_key = yaml.safe_load(stream)
        username = auth_key["username"]
        password = auth_key["password"]
    else:
        # ask user for login keys
        username, password = get_login_from_terminal(username, password)

    if username is None or password is None:
        # continue without authentication
        return None
    else:
        # Start the AuthSession
        session = requests.Session()
        # Create the payload
        payload = {
            "LOGIN1": "",
            "Y": username,
            "p": password,
            "X": "",
        }
        # Post the payload to the site to log in
        session.post(url_login, data=payload)
        return session


def get_login_from_terminal(
    username: Union[str, None],
    password: Union[str, None],
    file_auth: str = directory_project + "/config/authentication.yaml",
) -> Tuple[Union[str, None]]:
    """
    Get login key from user during run time if 'username' and/or 'password' is 'None'.
    Return 'None' if no reply within 15 sec.
    """
    if username is None or password is None:
        record = True
    else:
        record = False
    if username is None:
        username = ask_for_input("Enter your Email: ")
    if password is None:
        password = ask_for_input("Enter your Password: ")
    if record and isinstance(username, str) and isinstance(password, str):
        loginkey_to_file(username, password, file_auth)
    return username, password


def ask_for_input(request: str) -> Union[str, None]:
    timeout = 15
    end_time = time.time() + timeout
    while time.time() < end_time:
        reply = input(request)
        try:
            assert isinstance(reply, str)
            break
        except Exception:
            reply = None
            continue
    return reply


def loginkey_to_file(
    username: str,
    password: str,
    file_auth: str,
) -> None:
    """Safe login key to yaml"""
    file = open(file_auth, "w")
    file.write(f"username: '{username}'\n")
    file.write(f"password: '{password}'")
    file.close()


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


def labeled_blockmodel(g, partition):
    """
    Perform blockmodel transformation on graph *g*
    and partition represented by dictionary *partition*.
    Values of *partition* are used to partition the graph.
    Keys of *partition* are used to label the nodes of the
    new graph.
    """
    new_g = nx.quotient_graph(g, list(partition.values()), relabel=True)
    labels = dict(enumerate(partition.keys()))
    new_g = nx.relabel_nodes(new_g, labels)

    return new_g


def repartition_dataframe(df, partition):
    """
    Create a new dataframe with the same index as
    argument dataframe *df*, where columns are
    the keys of dictionary *partition*.
    The data of the returned dataframe are the
    combinations of columns listed in the keys of
    *partition*
    """
    df2 = pd.DataFrame(index=df.index)

    for k, v in list(partition.items()):
        df2[k] = df[v[0]]

        for i in range(len(v) - 1):
            df2[k] = df2[k] + df[v[i]]

    return df2


def get_common_head(str1, str2, delimiter=None):
    try:
        if str1 is None or str2 is None:
            return "", 0
        else:
            # this is ugly control flow clean it
            if delimiter is not None:

                dstr1 = str1.split(delimiter)
                dstr2 = str2.split(delimiter)

                for i in range(len(dstr1)):
                    if dstr1[:i] != dstr2[:i]:
                        # print list1[:i], list2[:i]
                        return delimiter.join(dstr1[: i - 1]), i - 1
                return str1, i
            else:
                for i in range(len(str1)):
                    if str1[:i] != str2[:i]:
                        # print list1[:i], list2[:i]
                        return str1[: i - 1], i - 1
                return str1[:i], i

        return "", 0
    except Exception as e:
        print(e)
        return "", 0


def get_common_foot(str1, str2, delimiter=None):
    head, ln = get_common_head(str1[::-1], str2[::-1], delimiter=delimiter)

    return head[::-1], ln


# turn these into automated tests
# print get_common_head('abcdefghijklmnop','abcde12345')
# print get_common_head('abcdefghijklmnop',None)
# print get_common_head('abcde\nfghijk\nlmnop\nqrst','abcde\nfghijk\nlmnopqr\nst',delimiter='\n')


def remove_quoted(mess):
    message = [
        line
        for line in mess.split("\n")
        if len(line) != 0 and line[0] != ">" and line[-6:] != "wrote:"
    ]
    new = "\n".join(message)
    return new


## remove this when clean_message is added to generic libraries
def clean_message(mess):
    if mess is None:
        mess = ""
    mess = remove_quoted(mess)
    mess = mess.strip()
    return mess


# From here:
# https://stackoverflow.com/questions/46217529/pandas-datetimeindex-frequency-is-none-and-cant-be-set
def add_freq(idx, freq=None):
    """Add a frequency attribute to idx, through inference or directly.

    Returns a copy.  If `freq` is None, it is inferred.
    """

    idx = idx.copy()
    if freq is None:
        if idx.freq is None:
            freq = pd.infer_freq(idx)
        else:
            return idx
    idx.freq = pd.tseries.frequencies.to_offset(freq)
    if idx.freq is None:
        raise AttributeError(
            "no discernible frequency found to `idx`.  Specify"
            " a frequency string with `freq`."
        )
    return idx
