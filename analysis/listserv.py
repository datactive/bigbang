import datetime
import email
import glob
import logging
import mailbox
import os
import re
import subprocess
import time
import warnings
from mailbox import mboxMessage
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse

import numpy as np
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup
from tqdm import tqdm

from config.config import CONFIG

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)


class ListservListWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class ListservArchiveWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


standards_release_date_3GPP = [3, 6, 9, 12]  #[month]

class ListservList:
    """

    Methods
    -------
    to_percentage
    iterate_from_name_addr
    get_messagecount_per_affiliations
    get_messagecount_per_affiliations
    get_messagecount_per_timezone
    get_members_per_affiliations
    get_membercount_per_affiliations
    """

    def to_percentage(arr: np.array) -> np.array:
        return arr / np.sum(arr)

    def iterate_from_name_addr(li: list) -> tuple:
        """ Generator that splits the 'from' header field. """
        domains = []
        for sender in  li:
            name, addr = email.utils.parseaddr(sender)
            if '@' in addr:
                localpart, domain = addr.split('@')
                yield name, localpart, domain
            else:
                yield name, None, None

    def get_messagecount_per_affiliations(
        df: pd.DataFrame, percentage: bool=False, contract: float=None,
    ) -> Dict[str, int]:
        """
        Get contribution of messages per affiliation.

        Args:
            df: DataFrame of mailing list.
            percentage: Whether to return count of messages percentage w.r.t. total.
            contract: If affiliations who contributed less than threshold should be
                contracted to one class named 'Others'.
        """
        # collect
        domains = [
            domain
            for _, _, domain in ListservList.iterate_from_name_addr(df["from"].values)
            if domain
        ]

        # count
        name, count = np.unique(domains, return_counts=True)
        count = np.array(count)
        # sort
        indx = np.argsort(count).astype(int)
        name = [name[ii] for ii in indx]
        count = count[indx]
        
        if percentage:
            count = to_percentage(count)
        
        if contract:
            idx_low = np.arange(len(count))[count < contract]
            idx_high = np.arange(len(count))[count >= contract]
            count_comp = list(count[idx_high]) + [np.sum(count[idx_low])]
            name_comp = [name[idx] for idx in idx_high] + ['Others']
            return {key: value for key, value in zip(name_comp, count_comp)}
        else:
            return {key: value for key, value in zip(name, count)}

    def get_members_per_affiliations(df: pd.DataFrame) -> Dict[str, int]:
        """
        Get contribution of members per affiliation.
        """
        # iterate through senders
        dic = {}
        for _, localpart, domain in ListservList.iterate_from_name_addr(df["from"].values):
            if domain is None:
                continue
            elif domain not in dic.keys():
                dic[domain] = []
            dic[domain].append(localpart)
        # remove duplicates
        dic = {domain: list(set(li)) for domain, li in dic.items()}
        return dic

    def get_membercount_per_affiliations(
        df: pd.DataFrame, percentage: bool=False, contract: float=None,
    ) -> Dict[str, int]:
        """
        Get contribution of members per affiliation.

        Args:
            df: DataFrame of mailing list.
            percentage: Whether to return count of messages percentage w.r.t. total.
            contract: If affiliations who contributed less than threshold should be
                contracted to one class named 'Others'.
        """
        # collect members per affiliation
        dic = ListservList.get_members_per_affiliations(df)
        # count members per affiliation
        dic = {domain: len(members) for domain, members in dic.items()}

        if percentage:
            total_member_nr = np.sum(list(dic.values()))
            dic = {
                domain: member_nr/total_member_nr
                for domain, member_nr in dic.items()
            }

        # sort low to high contribution
        domain = np.asarray(list(dic.keys()))
        count = np.asarray(list(dic.values()))
        indx = np.argsort(count).astype(int)
        domain = domain[indx]
        count = count[indx]
        
        if contract:
            idx_low = np.arange(len(count))[count < contract]
            idx_high = np.arange(len(count))[count >= contract]
            count_comp = list(count[idx_high]) + [np.sum(count[idx_low])]
            name_comp = [domain[idx] for idx in idx_high] + ['Others']
            return {key: value for key, value in zip(name_comp, count_comp)}
        else:
            return {key: value for key, value in zip(domain, count)}

    def get_messagecount_per_timezone(
        df: pd.DataFrame, percentage: bool=False,
    ) -> Dict[str, int]:
        """
        Get contribution of messages per time zone.

        Args:
            df: DataFrame of mailing list.
            percentage: Whether to return count of messages percentage w.r.t. total.
        """
        utcoffsets = [dt.utcoffset() for dt in df['date'].values]
        utcoffsets_hm = []
        for utcoffset in utcoffsets:
            if utcoffset.days == -1:
                _dt = utcoffset + datetime.timedelta(days=1)
                _dt = str(datetime.timedelta(days=1) - _dt)
                _hour, _min, _ = _dt.split(':')
                _hour = "-%02d" % int(_hour)
                _dt = (':').join([_hour, _min])
            else:
                _dt = str(utcoffset)
                _hour, _min, _ = _dt.split(':')
                _hour = "+%02d" % int(_hour)
                _dt = (':').join([_hour, _min])
            utcoffsets_hm.append(_dt)
        utcoffsets_hm, counts = np.unique(utcoffsets_hm, return_counts=True)
        return {td: cou for td, cou in zip(utcoffsets_hm, counts)}


class ListservArchive(ListservList):
    """
    Methods
    -------
        get_mlists_per_institution
    """

    def get_mlists_per_institution(df: pd.DataFrame) -> Dict[str, int]:
        """
        Get a dictionary that lists the mailing lists/working groups in which
        a institute/company is active.
        """
        dic_mlis = {}
        for mem in list(set(df['from'].values)):
            mlist_names = list(set(df[df['from'] == mem]['MailingList'].values))
            name, addr = email.utils.parseaddr(mem)
            try:
                localpart, domain = addr.split('@')
            except:
                continue
            if domain not in dic_mlis.keys():
                dic_mlis[domain] = []
            dic_mlis[domain] += mlist_names
        dic_mlis = {key: len(list(set(value))) for key, value in dic_mlis.items()}
        return dic_mlis

#def detect_falt():
#    keys_list = list(march.lists[0].messages[0].keys())
#
#    for ii, mlist in enumerate(march.lists):
#        for jj, msg in enumerate(mlist.messages):
#            if msg["Message-ID"] != None:
#                for key in msg.keys():
#                    if key not in keys_list:
#                        print(ii, jj, key, msg["Message-ID"])
