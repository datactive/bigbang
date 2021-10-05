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
from bigbang.utils import (
    get_paths_to_files_in_directory,
    get_paths_to_dirs_in_directory,
)

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)


class ListservListWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


class ListservArchiveWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


standards_release_date_3GPP = [3, 6, 9, 12]  # [month]
reply_labels = ["Re:", "AW:", "=?utf-8?b?J+etlOWkjTo=?="]


class ListservList:
    """
    Note
    ----
    Issues loading 3GPP_TSG_RAN_WG1 which is 3.3Gb large

    Methods
    -------
    classmethod:
        from_mbox
        from_pandas_dataframe
    staticmethod:
        to_percentage
        contract
        get_name_localpart_domain
        iterator_name_localpart_domain
    period_of_activity
    crop_by_year
    crop_by_address
    crop_by_subject
    get_domains
    get_domainscount
    get_localparts
    get_localpartscount
    - get_threads
    - get_threadscount
    get_messagecount
    get_messagecount_per_timezone
    get_sender_receiver_dictionary
    create_sender_receiver_digraph
    get_graph_prop_per_domain_per_year
    """

    def __init__(
        self,
        name: str,
        filepath: str,
        msgs: pd.DataFrame,
    ):
        self.name = name
        self.filepath = filepath
        self.df = msgs

    def __len__(self) -> int:
        return len(self.df.index.values)

    def __iter__(self):
        return iter(self.df.iterrows())

    @classmethod
    def from_mbox(
        cls,
        name: str,
        filepath: str,
        include_body: bool = True,
    ) -> "ListservList":
        msgs = ListservListIO.from_mbox(name, filepath)
        df = ListservListIO.to_pandas_dataframe(msgs, include_body)
        return cls.from_pandas_dataframe(df, name, filepath)

    @classmethod
    def from_pandas_dataframe(
        cls,
        df: pd.DataFrame,
        name: Optional[str] = None,
        filepath: Optional[str] = None,
    ) -> "ListservList":
        if "subject" in df.columns:
            # remove multiple spaces in string
            df["subject"] = df["subject"].apply(lambda x: re.sub(" +", " ", x))
        return cls(name, filepath, df)

    @staticmethod
    def to_percentage(arr: np.array) -> np.array:
        return arr / np.sum(arr)

    @staticmethod
    def contract(count: np.array, label: list, contract: float) -> dict:
        idx_low = np.arange(len(count))[count < contract]
        idx_high = np.arange(len(count))[count >= contract]
        count_comp = list(count[idx_high]) + [np.sum(count[idx_low])]
        name_comp = [label[idx] for idx in idx_high] + ["Others"]
        return {key: value for key, value in zip(name_comp, count_comp)}

    @staticmethod
    def get_name_localpart_domain(string: str) -> tuple:
        """
        Split an address field which has a format as
        'Heinrich von Kleist <Heinrich.vonKleist@SELBST.ORG>' into name,
        local-part, and domain.
        All strings are returned in lower case only to avoid duplicates.
        """
        name, addr = email.utils.parseaddr(string)
        addr = addr.split(" ")[-1]
        if "@" in addr:
            localpart, domain = addr.split("@")
            return name.lower(), localpart.lower(), domain.lower()
        else:
            return name.lower(), None, None

    @staticmethod
    def iterator_name_localpart_domain(li: list) -> tuple:
        """Generator for the self.get_name_localpart_domain() function."""
        for sender in li:
            yield ListservList.get_name_localpart_domain(sender)

    def period_of_activity(self) -> list:
        """
        Return a list containing the datetime of the first and last message
        written in the mailing list.
        """
        return [min(self.df["date"].values), max(self.df["date"].values)]

    def crop_by_year(self, yrs: Union[int, list]) -> "ListservList":
        """
        Filter self.df by year in message date.

        Returns
        -------
            'ListservList' object cropped to specification.
        """
        if isinstance(yrs, int) or isinstance(yrs, np.int64):
            mask = [dt.year == yrs for dt in self.df["date"].values]
        if isinstance(yrs, list):
            mask = [
                (dt.year >= min(yrs)) & (dt.year < max([yrs]))
                for dt in self.df["date"].values
            ]
        return ListservList.from_pandas_dataframe(
            df=self.df.loc[mask],
            name=self.name,
            filepath=self.filepath,
        )

    def crop_by_address(
        self,
        header_field: str,
        per_address_field: Dict[str, List[str]],
    ) -> "ListservList":
        """
        Parameters
        ----------
            header_field : For a Listserv mailing list the most representative
                header fields for senders and receivers are 'from' and
                'comments-to' respectively.
            per_address_field : Filter by 'local-part' or 'domain' part of an address.
                The data structure of the argument should be, e.g.:
                    {'localpart': [string-1, string-2, ...]}
        Returns
        -------
            'ListservList' object cropped to specification.
        """
        mlist = self
        indices = []
        indx = 0
        generator = ListservList.iterator_name_localpart_domain(
            mlist.df[header_field].dropna().values
        )
        for _, localpart, domain in generator:
            if "domain" in list(per_address_field.keys()):
                if domain in per_address_field["domain"]:
                    indices.append(indx)
            if "localpart" in list(per_address_field.keys()):
                if localpart in per_address_field["localpart"]:
                    indices.append(indx)
            indx += 1
        return ListservList.from_pandas_dataframe(
            df=mlist.df.iloc[indices],
            name=self.name,
            filepath=self.filepath,
        )

    def crop_by_subject(self, match=str) -> "ListservList":
        """
        Returns
        -------
            'ListservList' object cropped to message subject.
        """
        mask = [
            True if re.search(match, sb) else False
            for sb in self.df["subject"].values
        ]
        return ListservList.from_pandas_dataframe(
            df=self.df.loc[mask],
            name=self.name,
            filepath=self.filepath,
        )

    def get_domains(
        self,
        header_fields: List[str],
        return_counts: bool = False,
    ) -> dict:
        """
        Get contribution of members per affiliation.

        Note
        ----
            For a Listserv mailing list the most representative header fields
            of senders and receivers are 'from' and 'comments-to' respectively.

        Parameters
        ----------
            header_fields : Indicate which Email header field to process
                (e.g. 'from', 'reply-to', 'comments-to'). For a listserv
                mailing list the most representative header fields of
                senders and receivers are 'from' and 'comments-to' respectively.
            return_counts : If 'True', return # of messages per domain.
        """
        domains = {}
        for header_field in header_fields:
            generator = ListservList.iterator_name_localpart_domain(
                self.df[header_field].dropna().values
            )
            # collect domain labels
            _domains = [
                domain for _, _, domain in generator if domain is not None
            ]
            _domains_unique = list(set(_domains))
            if return_counts:
                _domains_unique = [
                    [du, _domains.count(du)] for du in _domains_unique
                ]
            domains[header_field] = _domains_unique
        return domains

    def get_domainscount(
        self,
        header_fields: List[str],
        per_year: bool = False,
    ) -> dict:
        """
        Parameters
        ----------
            header_fields : Indicate which Email header field to process
                (e.g. 'from', 'reply-to', 'comments-to'). For a listserv
                mailing list the most representative header fields of
                senders and receivers are 'from' and 'comments-to' respectively.
            per_year :
        """
        if per_year:
            dics = {}
            for header_field in header_fields:
                dics[header_field] = {}
                period_of_activity = self.period_of_activity()
                years = [dt.year for dt in period_of_activity]
                years = np.arange(min(years), max(years) + 1)

                for year in years:
                    mlist_fi = self.crop_by_year(year)
                    domains = mlist_fi.get_domains(
                        [header_field], return_counts=False
                    )
                    dics[header_field][year] = len(domains[header_field])
            return dics
        else:
            dic = self.get_domains(header_fields, return_counts=False)
            for header_field, domains in dic.items():
                dic[header_field] = len(domains)
            return dic

    def get_localparts(
        self,
        header_fields: List[str],
        per_domain: bool = False,
        return_counts: bool = False,
    ) -> dict:
        """
        Get contribution of members per affiliation.

        Parameters
        ----------
            header_fields : Indicate which Email header field to process
                (e.g. 'from', 'reply-to', 'comments-to'). For a listserv
                mailing list the most representative header fields of
                senders and receivers are 'from' and 'comments-to' respectively.
            per_domain :
            return_counts : If 'True', return # of messages per localpart.
        """
        localparts = {}
        for header_field in header_fields:
            if per_domain:
                # TODO: Needs two for loop. Find way to reduce it.
                localparts[header_field] = {}
                generator = ListservList.iterator_name_localpart_domain(
                    self.df[header_field].dropna().values
                )
                _domains = list(
                    set(
                        [
                            domain
                            for _, _, domain in generator
                            if domain is not None
                        ]
                    )
                )
                _localparts = {d: [] for d in _domains}
                generator = ListservList.iterator_name_localpart_domain(
                    self.df[header_field].dropna().values
                )
                for _, localpart, domain in generator:
                    if domain is not None:
                        _localparts[domain].append(localpart)
                for _domain, _dolps in _localparts.items():
                    _dolpsu = list(set(_dolps))
                    if return_counts:
                        _dolpsu = [[ll, _dolps.count(ll)] for ll in _dolpsu]
                    _localparts[_domain] = _dolpsu
                localparts[header_field] = _localparts
            else:
                generator = ListservList.iterator_name_localpart_domain(
                    self.df[header_field].dropna().values
                )
                _localparts = [
                    localpart
                    for _, localpart, domain in generator
                    if domain is not None
                ]
                _localparts_unique = list(set(_localparts))
                if return_counts:
                    _localparts_unique = [
                        [lpu, _localparts.count(lpu)]
                        for lpu in _localparts_unique
                    ]
                localparts[header_field] = _localparts_unique
        return localparts

    def get_localpartscount(
        self,
        header_fields: List[str],
        per_domain: bool = False,
        per_year: bool = False,
    ) -> dict:
        """
        Parameters
        ----------
            header_fields : Indicate which Email header field to process
                (e.g. 'from', 'reply-to', 'comments-to'). For a listserv
                mailing list the most representative header fields of
                senders and receivers are 'from' and 'comments-to' respectively.
            per_domain :
            per_year :
        """
        if per_year:
            dics = {}
            for header_field in header_fields:
                dics[header_field] = {}
                period_of_activity = self.period_of_activity()
                years = [dt.year for dt in period_of_activity]
                years = np.arange(min(years), max(years) + 1)

                for year in years:
                    dics[header_field][year] = {}
                    mlist_fi = self.crop_by_year(year)
                    dic_lp = mlist_fi.get_localparts(
                        [header_field], per_domain
                    )
                    if per_domain:
                        for domain, localparts in dic_lp[header_field].items():
                            dics[header_field][year][domain] = len(localparts)
                    else:
                        dics[header_field][year] = len(dic_lp[header_field])
            return dics
        else:
            dic = self.get_localparts(header_fields, per_domain)
            if per_domain:
                for header_field, domains in dic.items():
                    for domain, localparts in domains.items():
                        dic[header_field][domain] = len(localparts)
            else:
                for header_field, localparts in dic.items():
                    dic[header_field] = len(localparts)
            return dic

    def get_subjects(
        self,
        per_address_field: Optional[str] = None,
    ) -> Union[List[str], dict]:
        """
        Find all unique message subjects. Replies not treated as a new subject.

        Note
        ----
            i) Some Emails start with 'AW:', which comes from German and has
                the same meaning as 'Re:'.
            ii) Some Emails start with '=?utf-8?b?J+etlOWkjTo=?=', which is a
                UTF-8 encoding of the Chinese characters '答复' which has the
                same meaning as 'Re:'.
            iii) Leading strings such as 'FW:' are treated as new subjects.

        Parameters
        ----------
            per_address_field :
        """
        subjects = []
        indices = []
        print(self.df["subject"])
        for indx, sb in enumerate(self.df["subject"].values):
            subject_not_reply = []
            for rl in reply_labels:
                if rl not in sb[:25]:
                    subject_not_reply.append(True)
                else:
                    subject_not_reply.append(False)
            if all(subject_not_reply):
                subjects.append(sb)
                indices.append(indx)
        if per_address_field:
            generator = ListservList.iterator_name_localpart_domain(
                self.df.iloc[indices]["from"].values
            )
            if "domain" in per_address_field:
                domains = [domain for _, _, domain in generator]
                dics = {do: [] for do in list(set(domains)) if do is not None}
                for do, sb in zip(domains, subjects):
                    if do is not None:
                        dics[do].append(sb)
            elif "localpart" in per_address_field:
                localparts = [localpart for _, localpart, _ in generator]
                dics = {
                    lp: [] for lp in list(set(localparts)) if lp is not None
                }
                for lp, sb in zip(localparts, subjects):
                    if lp is not None:
                        dics[lp].append(sb)
            subjects = dics
        return subjects

    def get_subjectscount(
        self,
        per_address_field: Optional[str] = None,
    ) -> int:
        subjects = self.get_subjects(per_address_field)
        if per_address_field:
            return {key: len(values) for key, values in subjects.items()}
        else:
            return len(subjects)

    def get_messagecount(
        self,
        header_fields: Optional[List[str]] = None,
        per_address_field: Optional[str] = None,
        per_year: bool = False,
    ) -> dict:
        """
        Parameters
        ----------
            header_field :
            per_year :
        """
        if per_year:
            dics = {}
            for header_field in header_fields:
                dics[header_field] = {}
                period_of_activity = self.period_of_activity()
                years = [dt.year for dt in period_of_activity]
                years = np.arange(min(years), max(years) + 1)

                for year in years:
                    mlist_fi = self.crop_by_year(year)
                    if "domain" in per_address_field:
                        res = mlist_fi.get_domains(
                            [header_field],
                            return_counts=True,
                        )
                    elif "localpart" in per_address_field:
                        res = mlist_fi.get_localparts(
                            [header_field],
                            per_domain=False,
                            return_counts=True,
                        )
                    dics[header_field][year] = {
                        label: count for label, count in res[header_field]
                    }
            return dics
        if header_fields:
            if "domain" in per_address_field:
                res = self.get_domains(
                    header_fields,
                    return_counts=True,
                )
            elif "localpart" in per_address_field:
                res = self.get_localparts(
                    header_fields,
                    per_domain=False,
                    return_counts=True,
                )
            dics = {}
            for header_field, res in res.items():
                dics[header_field] = {label: count for label, count in res}
            return dics
        else:
            return len(self.df.index.values)

    def get_messagecount_per_timezone(
        self,
        percentage: bool = False,
    ) -> Dict[str, int]:
        """
        Get contribution of messages per time zone.

        Parameters
        ----------
            percentage: Whether to return count of messages percentage w.r.t. total.
        """
        utcoffsets = [dt.utcoffset() for dt in self.df["date"].values]
        utcoffsets_hm = []
        for utcoffset in utcoffsets:
            if utcoffset.days == -1:
                _dt = utcoffset + datetime.timedelta(days=1)
                _dt = str(datetime.timedelta(days=1) - _dt)
                _hour, _min, _ = _dt.split(":")
                _hour = "-%02d" % int(_hour)
                _dt = (":").join([_hour, _min])
            else:
                _dt = str(utcoffset)
                _hour, _min, _ = _dt.split(":")
                _hour = "+%02d" % int(_hour)
                _dt = (":").join([_hour, _min])
            utcoffsets_hm.append(_dt)
        utcoffsets_hm, counts = np.unique(utcoffsets_hm, return_counts=True)
        return {td: cou for td, cou in zip(utcoffsets_hm, counts)}

    def get_sender_receiver_dictionary(
        self,
        domains_of_interest: Optional[list] = None,
    ) -> Dict:
        """
        Returns
        -------
            Nested dictionary with first layer the 'from'/sender domain keys and
            the second layer the 'comments-to'/receiver domain keys with the
            integer indicating the number of messages between them.
        """
        _df = self.df[
            [
                "from",
                "comments-to",
            ]
        ].dropna()
        dic = {}
        for idx, row in _df.iterrows():
            if pd.isnull(row["comments-to"]) or pd.isnull(row["from"]):
                continue

            # decompose sender
            (
                f_name,
                f_localpart,
                f_domain,
            ) = ListservList.get_name_localpart_domain(row["from"])

            if f_domain not in dic.keys():
                dic[f_domain] = {}

            # formatting of 'comments-to' field
            _commentsto = [
                s2
                for s1 in row["comments-to"].split(",")
                for s2 in s1.split("cc:")
                if "@" in s2
            ]

            for _ct in _commentsto:
                # formatting of 'comments-to' field
                _ct = re.sub(r"\((.*?)\)", "", _ct).strip()
                _ct = re.sub(r"\"", "", _ct).strip()
                # decompose receiver
                (
                    ct_name,
                    ct_localpart,
                    ct_domain,
                ) = ListservList.get_name_localpart_domain(_ct)
                # counting the messages
                if ct_domain not in dic[f_domain].keys():
                    dic[f_domain][ct_domain] = 1
                else:
                    dic[f_domain][ct_domain] += 1

        if domains_of_interest is not None:
            dic_doi = {}
            for sender, receivers in dic.items():
                for receiver, nr_msgs in receivers.items():
                    if sender in domains_of_interest:
                        if sender not in dic_doi.keys():
                            dic_doi[sender] = {}
                        dic_doi[sender][receiver] = nr_msgs

                    if receiver in domains_of_interest:
                        if sender not in dic_doi.keys():
                            dic_doi[sender] = {}
                        dic_doi[sender][receiver] = nr_msgs
            dic = dic_doi

        return dic

    def create_sender_receiver_digraph(
        self,
        nw: Optional[dict] = None,
        domains_of_interest: Optional[list] = None,
    ):
        """
        Create directed graph from messaging network created with
        ListservList.get_sender_receiver_dictionary().

        Parameters
        ----------
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
        self,
        years: Optional[tuple] = None,
        func=nx.betweenness_centrality,
    ) -> dict:
        if years is None:
            period_of_activity = self.period_of_activity()
            years = [dt.year for dt in period_of_activity]

        dic_evol = {}
        for year in np.arange(min(years), max(years) + 1):
            mlist_fi = self.crop_by_year(year)
            mlist_fi.create_sender_receiver_digraph()

            adj = func(mlist_fi.dg)

            labels = list(adj.keys())
            values = np.array(list(adj.values()))

            for lab, val in zip(labels, values):
                if lab not in list(dic_evol.keys()):
                    dic_evol[lab] = {
                        "year": [year],
                        "betweenness_centrality": [val],
                    }
                else:
                    dic_evol[lab]["year"].append(year)
                    dic_evol[lab]["betweenness_centrality"].append(val)
        return dic_evol


class ListservArchive:
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
            mlist["mailing-list"] = name
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
        for mem in list(set(self.df["from"].values)):
            mlist_names = list(
                set(self.df[self.df["from"] == mem]["mailing-list"].values)
            )
            name, addr = email.utils.parseaddr(mem)
            try:
                localpart, domain = addr.split("@")
            except Exception:
                continue
            if domain not in dic_mlis.keys():
                dic_mlis[domain] = []
            dic_mlis[domain] += mlist_names
        dic_mlis = {
            key: len(list(set(value))) for key, value in dic_mlis.items()
        }
        return dic_mlis


# def detect_falt():
#    keys_list = list(march.lists[0].messages[0].keys())
#
#    for ii, mlist in enumerate(march.lists):
#        for jj, msg in enumerate(mlist.messages):
#            if msg["Message-ID"] != None:
#                for key in msg.keys():
#                    if key not in keys_list:
#                        print(ii, jj, key, msg["Message-ID"])
