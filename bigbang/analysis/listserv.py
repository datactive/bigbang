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

import networkx as nx
import numpy as np
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup
from tqdm import tqdm

from config.config import CONFIG

from bigbang.io import ListservMessageIO, ListservListIO, ListservArchiveIO

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
    from_mbox
    period_of_activity
    to_percentage
    get_name_localpart_domain
    iterator_name_localpart_domain
    get_messagecount_per_domain
    get_messagecount_per_timezone
    get_localpartcount_per_domain
    get_sender_receiver_dictionary
    create_sender_receiver_digraph
    """

    def __init__(
        self, name: str, filepath: str, msgs: pd.DataFrame,
    ):
        self.name = name
        self.filepath = filepath
        self.df = msgs

    @classmethod
    def from_mbox(
        cls, name: str, filepath: str, include_body: bool=True,
    ) -> "ListservList":
        msgs = ListservListIO.from_mbox(name, filepath)
        df = ListservListIO.to_pandas_dataframe(msgs, include_body)
        return cls.from_pandas_dataframe(df, name, filepath)
    
    @classmethod
    def from_pandas_dataframe(
        cls,
        df: pd.DataFrame,
        name: Optional[str]=None,
        filepath: Optional[str]=None,
    ) -> "ListservList":
        return cls(name, filepath, df)
    
    def __len__(self) -> int:
        return len(df.index.values)

    def filter_by_year(self, yrs: Union[int, list]) -> pd.DataFrame:
        if isinstance(yrs, int) or isinstance(yrs, np.int64):
            mask = [dt.year == yrs for dt in self.df['date'].values]
        if isinstance(yrs, list):
            mask = [
                (dt.year >= min(yrs)) & (dt.year < max([yrs])) 
                for dt in self.df['date'].values
            ]
        return self.df.loc[mask]

    def period_of_activity(self) -> list:
        """
        Return a list containing the datetime of the first and last message
        written in the mailing list.
        """
        return [min(self.df['date'].values), max(self.df['date'].values)]

    @staticmethod
    def to_percentage(arr: np.array) -> np.array:
        return arr / np.sum(arr)

    @staticmethod
    def get_name_localpart_domain(string: str) -> tuple:
        name, addr = email.utils.parseaddr(string)
        if '@' in addr:
            localpart, domain = addr.split('@')
            return name, localpart, domain
        else:
            return name, None, None

    @staticmethod
    def iterator_name_localpart_domain(li: list) -> tuple:
        """ Generator that splits the 'from' header field. """
        for sender in  li:
            yield ListservList.get_name_localpart_domain(sender)

    def get_messagecount_per_domain(
        self, percentage: bool=False, contract: float=None,
    ) -> Dict[str, int]:
        """
        Get contribution of messages per affiliation.

        Args:
            percentage: Whether to return count of messages percentage w.r.t. total.
            contract: If affiliations who contributed less than threshold should be
                contracted to one class named 'Others'.
        """
        # collect
        domains = [
            domain
            for _, _, domain in ListservList.iterator_name_localpart_domain(self.df["from"].values)
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
            count = ListservList.to_percentage(count)
        
        if contract:
            idx_low = np.arange(len(count))[count < contract]
            idx_high = np.arange(len(count))[count >= contract]
            count_comp = list(count[idx_high]) + [np.sum(count[idx_low])]
            name_comp = [name[idx] for idx in idx_high] + ['Others']
            return {key: value for key, value in zip(name_comp, count_comp)}
        else:
            return {key: value for key, value in zip(name, count)}

    def get_localpart_per_domain(self) -> Dict[str, int]:
        """
        Get contribution of members per affiliation.
        """
        # iterate through senders
        dic = {}
        for _, localpart, domain in ListservList.iterator_name_localpart_domain(self.df["from"].values):
            if domain is None:
                continue
            elif domain not in dic.keys():
                dic[domain] = []
            dic[domain].append(localpart)
        # remove duplicates
        dic = {domain: list(set(li)) for domain, li in dic.items()}
        return dic

    def get_localpartcount_per_domain(
        self, percentage: bool=False, contract: float=None,
    ) -> Dict[str, int]:
        """
        Get contribution of members per affiliation.

        Args:
            percentage: Whether to return count of messages percentage w.r.t. total.
            contract: If affiliations who contributed less than threshold should be
                contracted to one class named 'Others'.
        """
        # collect members per affiliation
        dic = ListservList.get_localpart_per_domain(self.df)
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
        self, percentage: bool=False,
    ) -> Dict[str, int]:
        """
        Get contribution of messages per time zone.

        Args:
            percentage: Whether to return count of messages percentage w.r.t. total.
        """
        utcoffsets = [dt.utcoffset() for dt in self.df['date'].values]
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

    def get_sender_receiver_dictionary(self) -> Dict:
        """
        Args:
            df: pd.DataFrame that contains 'from' and 'comments-to' header fields.

        Returns:
            Nested dictionary with first layer the 'from'/sender keys and the
            second layer the 'comments-to'/receiver keys with the integer
            indicating the number of messages between them.
        """
        _df = self.df[["from", "comments-to",]].dropna()
        dic = {}
        for idx, row in _df.iterrows():
            if pd.isnull(row["comments-to"]) or pd.isnull(row["from"]):
                continue
            
            # decompose sender
            f_name, f_localpart, f_domain = ListservList.get_name_localpart_domain(row["from"])

            if f_domain not in dic.keys():
                dic[f_domain] = {}
                
            # formatting of 'comments-to' field
            _commentsto = [
                s2
                for s1 in row["comments-to"].split(',')
                for s2 in s1.split('cc:')
                if '@' in s2
            ]
            
            for _ct in _commentsto:
                # formatting of 'comments-to' field
                _ct = re.sub(r'\((.*?)\)', '', _ct).strip()
                _ct = re.sub(r'\"', '', _ct).strip()
                # decompose receiver
                ct_name, ct_localpart, ct_domain = ListservList.get_name_localpart_domain(_ct)
                # counting the messages
                if ct_domain not in dic[f_domain].keys():
                    dic[f_domain][ct_domain] = 1
                else:
                    dic[f_domain][ct_domain] += 1
        return dic

    def create_sender_receiver_digraph(self, nw: Optional[dict]=None):
        """
        Create directed graph from messaging network created with
        ListservList.get_messaging_network_dictionary().

        Args:
            nw: dictionary created with ListservList.get_sender_receiver_dictionary()
        """
        if nw is None:
            nw = self.get_sender_receiver_dictionary()
        # initialise graph
        DG = nx.DiGraph()
        # create nodes
        [DG.add_node(sender) for sender in nw.keys()]
        [
            DG.add_node(receiver)
            for receivers in nw.values()
            for receiver in receivers.keys()
        ]
        # create edges
        for sender, receivers in nw.items():
            for receiver, nr_msgs in receivers.items():
                DG.add_edge(sender, receiver, weight=nr_msgs)
        # attach directed graph to class
        self.dg = DG

    def get_domain_betweenness_centrality_per_year() -> dict:
        dic_evol = {}
        period_of_activity = mlist_al.period_of_activity()
        years_of_activity = [dt.year for dt in period_of_activity]

        for year in np.arange(min(years_of_activity), max(years_of_activity)+1):
            df_al_fi = mlist_al.filter_by_year(year)
            mlist_al_fi = MList(df_al_fi)    
            mlist_al_fi.create_sender_receiver_digraph()

            adj = nx.betweenness_centrality(mlist_al_fi.dg)

            labels = list(adj.keys())
            values = np.array(list(adj.values()))
            
            for lab, val in zip(labels, values):
                if lab not in list(dic_evol.keys()):
                    dic_evol[lab] = {"year": [year], "betweenness_centrality": [val]}
                else:
                    dic_evol[lab]["year"].append(year)
                    dic_evol[lab]["betweenness_centrality"].append(val)


class ListservArchive():
    """
    Methods
    -------
        get_mlistscount_per_institution
    """

    def get_mlistscount_per_institution(df: pd.DataFrame) -> Dict[str, int]:
        """
        Get a dictionary that lists the mailing lists/working groups in which
        a institute/company is active.
        """
        dic_mlis = {}
        for mem in list(set(df['from'].values)):
            mlist_names = list(set(df[df['from'] == mem]['mailing-list'].values))
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
