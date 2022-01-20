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
