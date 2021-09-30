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
from bigbang.utils import get_paths_to_files_in_directory, get_paths_to_dirs_in_directory

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
    get_graph_prop_per_domain_per_year
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
    def contract(count: np.array, label: list, contract: float) -> dict:
        idx_low = np.arange(len(count))[count < contract]
        idx_high = np.arange(len(count))[count >= contract]
        count_comp = list(count[idx_high]) + [np.sum(count[idx_low])]
        name_comp = [label[idx] for idx in idx_high] + ['Others']
        return {key: value for key, value in zip(name_comp, count_comp)}

    @staticmethod
    def get_name_localpart_domain(string: str) -> tuple:
        """
        Returns only lower case strings to avoid duplicates.
        """
        name, addr = email.utils.parseaddr(string)
        addr = addr.split(' ')[-1]
        if '@' in addr:
            localpart, domain = addr.split('@')
            return name.lower(), localpart.lower(), domain.lower()
        else:
            return name.lower(), None, None

    @staticmethod
    def iterator_name_localpart_domain(li: list) -> tuple:
        """ Generator that splits the 'from' header field. """
        for sender in  li:
            yield ListservList.get_name_localpart_domain(sender)

    def get_messagecount_per_domain(
        self,
        percentage: bool=False,
        contract: float=None,
        per_year: bool=False,
    ) -> Dict[str, int]:
        """
        Get contribution of messages per affiliation.

        Args:
            percentage: Whether to return count of messages percentage w.r.t. total.
            contract: If affiliations who contributed less than threshold should be
                contracted to one class named 'Others'.
            per_year:
        """
        if per_year:
            period_of_activity = self.period_of_activity()
            years = [dt.year for dt in period_of_activity]
            dic_yrs = {}
            for year in np.arange(min(years), max(years)+1):
                mlist_fi = ListservList.from_pandas_dataframe(
        
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
            return ListservList.contract(count, name)
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

    def _get_localpartcount_per_domain(
        self, percentage: bool=False, contract: float=None,
    ) -> Dict[str, int]:
        # count
        dic = self.get_localpart_per_domain()
        domains = list(dic.keys())
        counts = np.array([len(localparts) for localparts in dic.values()])
        # sort low to high contribution
        indx = np.argsort(counts).astype(int)
        domains = [domains[ii] for ii in indx]
        counts = counts[indx]
        if percentage:
            counts = ListservList.to_percentage(counts)
        if contract:
            dic = ListservList.contract(counts, domains, contract)
        else:
            dic = {key: value for key, value in zip(domain, counts)}
        return dic

    def get_localpartcount(
        self,
        percentage: bool=False,
        contract: float=None,
        per_domain: bool=False,
        per_year: bool=False,
    ) -> Dict[str, int]:
        """
        Get contribution of members per affiliation.

        Args:
            percentage: Whether to return count of messages percentage w.r.t. total.
            contract: If affiliations who contributed less than threshold should be
                contracted to one class named 'Others'.
            per_year:
            per_domain:
        """
        if per_year:
            period_of_activity = self.period_of_activity()
            years = [dt.year for dt in period_of_activity]
            years = np.arange(min(years), max(years)+1)

            dic_yrs = {}
            for year in years:
                mlist_fi = ListservList.from_pandas_dataframe(
                    df=self.filter_by_year(year)
                )
                dic = mlist_fi._get_localpartcount_per_domain(percentage, contract)

                if per_domain:
                    # count members per affiliation
                    for domain, localparts in dic.items():
                        if domain not in list(dic_yrs.keys()):
                            dic_yrs[domain] = {
                                "year": [year], "localparts": [len(localparts)]
                            }
                        else:
                            dic_yrs[domain]["year"].append(year)
                            dic_yrs[domain]["localparts"].append(len(localparts))
                else:
                    dic_yrs[year] = np.sum(np.array(dic.values()))
            return dic_yrs
        else:
            dic = self._get_localpartcount_per_domain(percentage, contract)
            if per_domain:
                return dic
            else:
                return np.sum(np.array(list(dic.values())))
        
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

    def get_sender_receiver_dictionary(
        self,
        domains_of_interest: Optional[list]=None,
    ) -> Dict:
        """
        Returns:
            Nested dictionary with first layer the 'from'/sender domain keys and
            the second layer the 'comments-to'/receiver domain keys with the
            integer indicating the number of messages between them.
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

        if domains_of_interest is not None:
            dic_doi = {}
            for sender, receivers in dic.items():
                for receiver, nr_msgs in receivers.items():
                    if (sender in domains_of_interest):
                        if sender not in dic_doi.keys():
                            dic_doi[sender] = {}
                        dic_doi[sender][receiver] = nr_msgs
                    
                    if (receiver in domains_of_interest):
                        if sender not in dic_doi.keys():
                            dic_doi[sender] = {}
                        dic_doi[sender][receiver] = nr_msgs
            dic = dic_doi

        return dic

    def create_sender_receiver_digraph(
        self,
        nw: Optional[dict]=None,
        domains_of_interest: Optional[list]=None,
    ):
        """
        Create directed graph from messaging network created with
        ListservList.get_sender_receiver_dictionary().

        Args:
            nw: dictionary created with ListservList.get_sender_receiver_dictionary()
        """
        if nw is None:
            nw = self.get_sender_receiver_dictionary(domains_of_interest)
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

    def get_graph_prop_per_domain_per_year(
        self, years: Optional[tuple]=None, func=nx.betweenness_centrality,
    ) -> dict:
        if years is None:
            period_of_activity = self.period_of_activity()
            years = [dt.year for dt in period_of_activity]

        dic_evol = {}
        for year in np.arange(min(years), max(years)+1):
            mlist_fi = ListservList.from_pandas_dataframe(df=self.filter_by_year(year))
            mlist_fi.create_sender_receiver_digraph()

            adj = func(mlist_fi.dg)

            labels = list(adj.keys())
            values = np.array(list(adj.values()))
            
            for lab, val in zip(labels, values):
                if lab not in list(dic_evol.keys()):
                    dic_evol[lab] = {"year": [year], "betweenness_centrality": [val]}
                else:
                    dic_evol[lab]["year"].append(year)
                    dic_evol[lab]["betweenness_centrality"].append(val)
        return dic_evol


class ListservArchive():
    """
    Parameters
    ----------
    name
        The of whom the archive is (e.g. 3GPP, IEEE, ...)
    filedsc
        The file description of the archive
    lists
        A list containing the mailing lists as `ListservList` types

    Methods
    -------
        get_mlistscount_per_institution
    """

    def __init__(self, name: str, filedsc: str, lists: pd.DataFrame):
        self.name = name
        self.filedsc = filedsc
        self.df = lists

    @classmethod
    def from_mbox(
        cls,
        name: str,
        directorypath: str,
        filedsc: str = "*.mbox",
    ) -> "ListservArchive":
        filepaths = get_paths_to_files_in_directory(directorypath, filedsc)
        if len(filepaths) > 0:
            ListservArchiveWarning("No files found fitting the description")
        for count, filepath in enumerate(filepaths):
            name = filepath.split("/")[-1].split(".")[0]
            mlist = ListservList.from_mbox(name, filepath).df
            mlist['mailing-list'] = name
            if count == 0:
                mlists = mlist
            else:
                mlists = mlists.append(mlist, ignore_index=True)
        return cls(name, directorypath + filedsc, mlists)

    def get_mlistscount_per_institution(self) -> Dict[str, int]:
        """
        Get a dictionary that lists the mailing lists/working groups in which
        a institute/company is active.
        """
        dic_mlis = {}
        for mem in list(set(self.df['from'].values)):
            mlist_names = list(set(self.df[self.df['from'] == mem]['mailing-list'].values))
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
