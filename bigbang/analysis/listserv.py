import copy
import datetime
import email
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

import networkx as nx
import numpy as np
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from bigbang.config import CONFIG

import bigbang.bigbang_io as bio
from bigbang.utils import (
    get_paths_to_files_in_directory,
    get_paths_to_dirs_in_directory,
)
from bigbang.analysis.utils import (
    get_index_of_msgs_with_subject,
    get_index_of_msgs_with_datetime,
)

filepath_auth = CONFIG.config_path + "authentication.yaml"
directory_project = str(Path(os.path.abspath(__file__)).parent.parent)
logging.basicConfig(
    filename=directory_project + "/listserv.analysis.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)

# Turn off pandas SettingWithCopyWarning warning
pd.options.mode.chained_assignment = None

# Indicators that a message is a reply
reply_labels = [
    "Re:",
    "Re\xa0",
    "AW:",
    "=?utf-8?b?J+WbnuWkjTo=?=",
    "=?utf-8?b?J+etlOWkjTo=?=",
]
# =?utf-8?b?J++9llNSVkND?=


class ListservMailListWarning(BaseException):
    """Base class for ListservMailList class specific exceptions"""

    pass


class ListservMailListDomainWarning(BaseException):
    """Base class for ListservMailListDomain class specific exceptions"""

    pass


class ListservMailList:
    """
    Note
    ----
    Issues loading 3GPP_TSG_RAN_WG1 which is 3.3Gb large
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
        """Get number of messsages within the mailing list."""
        return len(self.df.index.values)

    def __iter__(self):
        """Iterate over each message within the mailing list."""
        return iter(self.df.iterrows())

    @classmethod
    def from_mbox(
        cls,
        name: str,
        filepath: str,
        include_body: bool = True,
    ) -> "ListservMailList":
        df = bio.mlist_from_mbox_to_pandas_dataframe(filepath)
        return cls.from_pandas_dataframe(df, name, filepath)

    @classmethod
    def from_pandas_dataframe(
        cls,
        df: pd.DataFrame,
        name: Optional[str] = None,
        filepath: Optional[str] = None,
    ) -> "ListservMailList":
        return cls(name, filepath, df)

    @staticmethod
    def to_percentage(arr: np.array) -> np.array:
        return arr / np.sum(arr)

    @staticmethod
    def contract(count: np.array, label: list, contract: float) -> Dict[str, int]:
        """
        This function contracts all domain names that contributed to a mailinglists
        below the `contract` threshold into one entity called `Others`. Meaning,
        if `contract=3` and `nokia.com`, `nokia.com`, `t-mobile.at` all wrote less
        then three Emails to the mailinglist in question, their contributions are
        going to be summed into one entity denoted as `Others`.

        Parameters
        ----------
        count : Number of Emails send to mailinglist.
        label : Names of contributers to mailinglist.
        contract : Threshold below which all contributions will be summed.
        """
        idx_low = np.arange(len(count))[count < contract]
        idx_high = np.arange(len(count))[count >= contract]
        count_comp = list(count[idx_high]) + [np.sum(count[idx_low])]
        name_comp = [label[idx] for idx in idx_high] + ["Others"]
        return {key: value for key, value in zip(name_comp, count_comp)}

    @staticmethod
    def get_name_localpart_domain(string: str) -> tuple:
        """
        Split an address field which has (ideally) a format as
        'Heinrich von Kleist <Heinrich.vonKleist@SELBST.org>' into name,
        local-part, and domain.
        All strings are returned in lower case only to avoid duplicates.

        Note
        ----
        Test whether the incorporation of email.utils.parseaddr() can improve
        this function.
        """
        # test if name is in string or if address is duplicated
        test = string.split(" ")
        if (len(test) == 2) and all("@" in st for st in test) and (test[0] == test[1]):
            # identifies addresses of the form:
            # localpart@domain localpart@domain
            addr = test[0]
            localpart, domain = addr.split("@")
            return None, localpart.lower(), domain.lower()
        elif (len(test) > 2) and ("@" in test[-1]):
            # identifies addresses of the form:
            # abc def ghi localpart@domain
            name = (" ").join(test[:-1])
            name = name.replace('"', "").replace('"', "")
            addr = test[-1]
            addr = addr.replace("<", "").replace(">", "")
            localpart, domain = addr.split("@")
            return name.lower(), localpart.lower(), domain.lower()
        else:
            # identifies addresses of the form:
            # abc localpart@domain
            name = string.split(" ")[0]
            name = name.replace('"', "")
            addr = string.split(" ")[-1]
            addr = addr.replace("<", "").replace(">", "")
            if "@" in addr:
                localpart, domain = addr.split("@")
                return name.lower(), localpart.lower(), domain.lower()
            else:
                logger.info(
                    f"The localpart and domain could not be obtained from the "
                    f"address: {string}"
                )
                return name.lower(), None, None

    @staticmethod
    def iterator_name_localpart_domain(li: list) -> tuple:
        """Generator for the self.get_name_localpart_domain() function."""
        for string in li:
            # identify whether there are multiple addresses in one header field
            if (string.count("<") > 1) and (string.count(">") > 1):
                addresses = re.findall(r"(?<=\<).+?(?=\>)", string)
                for addr in addresses:
                    if "@" in addr:
                        yield ListservMailList.get_name_localpart_domain(addr)
                    else:
                        continue
            else:
                yield ListservMailList.get_name_localpart_domain(string)

    def period_of_activity(
        self,
        format: str = "%a, %d %b %Y %H:%M:%S %z",
    ) -> list:
        """
        Return a list containing the datetime of the first and last message
        written in the mailing list.
        """
        indices = get_index_of_msgs_with_datetime(self.df)
        if not isinstance(self.df.loc[indices[0], "date"], datetime.datetime):
            self.df["date"] = pd.to_datetime(
                self.df["date"],
                format=format,
                errors="coerce",
            )
        period_of_activity = [
            min(self.df.loc[indices, "date"].values),
            max(self.df.loc[indices, "date"].values),
        ]
        return period_of_activity

    def crop_by_year(self, yrs: Union[int, list]) -> "ListservMailList":
        """
        Filter `self.df` DataFrame by year in message date.

        Parameters
        ----------
        yrs : Specify a specific year, such as 2021, or a range of years, such
            as [2011, 2021].

        Returns
        -------
        `ListservMailList` object cropped to specification.
        """
        index = get_index_of_msgs_with_datetime(self.df)
        _df = self.df.loc[index]
        if isinstance(yrs, int) or isinstance(yrs, np.int64):
            mask = [dt.year == yrs for dt in _df["date"].values]
        if isinstance(yrs, list):
            mask = [
                (dt.year >= min(yrs)) & (dt.year < max(yrs))
                for dt in _df["date"].values
            ]
        return ListservMailList.from_pandas_dataframe(
            df=_df.loc[mask],
            name=self.name,
            filepath=self.filepath,
        )

    def crop_by_address(
        self,
        header_field: str,
        per_address_field: Dict[str, List[str]],
    ) -> "ListservMailList":
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
        `ListservMailList` object cropped to specification.
        """
        mlist = self.df.dropna(subset=["from"])
        if "domain" in list(per_address_field.keys()):
            _addr = pd.Series(
                [
                    ListservMailList.get_name_localpart_domain(addr)[-1]
                    for addr in mlist["from"].values
                ],
                index=mlist.index.values,
            ).dropna()
            mlist = mlist.loc[_addr.index]
            mlist = mlist[_addr.isin(per_address_field["domain"])]
        if "localpart" in list(per_address_field.keys()):
            _addr = pd.Series(
                [
                    ListservMailList.get_name_localpart_domain(addr)[1]
                    for addr in mlist["from"].values
                ],
                index=mlist.index.values,
            ).dropna()
            mlist = mlist.loc[_addr.index]
            mlist = mlist[_addr.isin(per_address_field["localpart"])]
        return ListservMailList.from_pandas_dataframe(
            df=mlist,
            name=self.name,
            filepath=self.filepath,
        )

    def crop_by_subject(self, match=str, place: int = 2) -> "ListservMailList":
        """
        Parameters
        ----------
        match : Only keep messages with subject lines containing `match` string.
        place : Define how to filter for `match`. Use on of the following methods:
            0 = Using Regex expression
            1 = String ends with match
            2 =

        Returns
        -------
        `ListservMailList` object cropped to message subject.
        """
        index = get_index_of_msgs_with_subject(self.df)
        _df = self.df.loc[index]
        if place == 0:
            func = lambda x: True if re.search(re.escape(match), x) else False
        elif place == 1:
            func = lambda x: True if x.endswith(match) else False
        else:
            func = (
                lambda x: True
                if any(
                    [
                        len(x.replace(match, "").replace(rl, "").replace(" ", "")) == 0
                        for rl in reply_labels
                    ]
                )
                else False
            )
        mask = _df["subject"].apply(func).values  # returns bool-type array
        return ListservMailList.from_pandas_dataframe(
            df=_df.loc[mask],
            name=self.name,
            filepath=self.filepath,
        )

    def get_domains(
        self,
        header_fields: List[str],
        return_msg_counts: bool = False,
        df: Optional[pd.DataFrame] = None,
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
        return_msg_counts : If 'True', return # of messages per domain.
        """
        if df is None:
            df = self.df
        domains = {}
        for header_field in header_fields:
            generator = ListservMailList.iterator_name_localpart_domain(
                df[header_field].dropna().values
            )
            # collect domain labels
            _domains = [domain for _, _, domain in generator if domain is not None]
            _domains_unique = list(set(_domains))
            if return_msg_counts:
                _domains_unique = [[du, _domains.count(du)] for du in _domains_unique]
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
        per_year : Aggregate results for each year.

        Return
        ------
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
                        [header_field],
                        return_msg_counts=False,
                        df=mlist_fi.df,
                    )
                    dics[header_field][year] = len(domains[header_field])
            return dics
        else:
            dic = self.get_domains(header_fields, return_msg_counts=False)
            for header_field, domains in dic.items():
                dic[header_field] = len(domains)
            return dic

    def get_localparts(
        self,
        header_fields: List[str],
        per_domain: bool = False,
        return_msg_counts: bool = False,
        df: Optional[pd.DataFrame] = None,
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
        return_msg_counts : If 'True', return # of messages per localpart.
        """
        if df is None:
            df = self.df
        localparts = {}
        for header_field in header_fields:
            if per_domain:
                # TODO: Needs two for loop. Find way to reduce it.
                localparts[header_field] = {}
                generator = ListservMailList.iterator_name_localpart_domain(
                    df[header_field].dropna().values
                )
                _domains = list(
                    set([domain for _, _, domain in generator if domain is not None])
                )
                _localparts = {d: [] for d in _domains}
                generator = ListservMailList.iterator_name_localpart_domain(
                    df[header_field].dropna().values
                )
                for _, localpart, domain in generator:
                    if domain is not None:
                        _localparts[domain].append(localpart)
                for _domain, _dolps in _localparts.items():
                    _dolpsu = list(set(_dolps))
                    if return_msg_counts:
                        _dolpsu = [[ll, _dolps.count(ll)] for ll in _dolpsu]
                    _localparts[_domain] = _dolpsu
                localparts[header_field] = _localparts
            else:
                generator = ListservMailList.iterator_name_localpart_domain(
                    df[header_field].dropna().values
                )
                _localparts = [
                    localpart
                    for _, localpart, domain in generator
                    if domain is not None
                ]
                _localparts_unique = list(set(_localparts))
                if return_msg_counts:
                    _localparts_unique = [
                        [lpu, _localparts.count(lpu)] for lpu in _localparts_unique
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
        per_domain : Aggregate results for each domain.
        per_year : Aggregate results for each year.

        Returns
        -------
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
                        [header_field], per_domain, df=mlist_fi.df
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

    def add_thread_info(self):
        """
        Edit pd.DataFrame to include extra column to identify which thread
        a message belongs to.

        Returns
        -------
        """
        # get thread subjects
        threads_root = self.get_threadsroot()
        # initialise new columns
        indices = []
        nr_thread = []
        # run through subjects and find associated messages
        for index, tsb in enumerate(threads_root.keys()):
            _mlist_fi = self.crop_by_subject(match=tsb)
            indices += list(_mlist_fi.df.index.values)
            nr_thread += [index] * len(_mlist_fi.df.index.values)
        # add new columns to pd.DataFrame
        self.df["thread"] = np.nan
        self.df.loc[indices, "thread"] = nr_thread

    def get_threads(
        self,
        return_length: bool = False,
    ) -> dict:
        """
        Collect all messages that belong to the same thread.

        Note
        ----
            Computationally very intensive.

        Parameters
        ----------
        return_length :
            If 'True', the returned dictionary will be of the form
            {'subject1': # of messages, 'subject2': # of messages, ...}.
            If 'False', the returned dictionary will be of the form
            {'subject1': list of indices, 'subject2': list of indices, ...}.

        Returns
        -------
        """
        mlist = self
        mlist.df = self.df.reset_index()
        threads_root = self.get_threadsroot()
        threads = {tsb: [] for tsb in threads_root.keys()}
        for tsb in threads_root.keys():
            mlist_fi = mlist.crop_by_subject(match=tsb)
            threads[tsb] += list(mlist_fi.df.index.values)
        if return_length:
            threads = {key: len(values) for key, values in threads.items()}
        return threads

    def get_threadsroot(
        self,
        per_address_field: Optional[str] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> dict:
        """
        Find all unique message subjects. Replies not treated as a new subject.

        Note
        ----
        The most reliable ways to find the beginning of threads is to check
        whether the subject line of a message contains an element of
        reply_labels at the beginning. Checking whether the header field
        'comments-to' is empty is not reliable, as 'reply-all' is often chosen
        by mistake as seen here:
        2020-04-01 10:08:58+00:00 joern.krause@etsi.org, juergen.hofmann@nokia.com
        2020-03-26 21:41:27+00:00 joern.krause@etsi.org NaN
        2020-03-26 21:00:08+00:00 joern.krause@etsi.org	juergen.hofmann@nokia.com

        i) Some Emails start with 'AW:', which comes from German and has
            the same meaning as 'Re:'.
        ii) Some Emails start with '=?utf-8?b?J+WbnuWkjTo=?=' or
            '=?utf-8?b?J+etlOWkjTo=?=', which are UTF-8 encodings of the
            Chinese characters '回复' and '答复' both of which have the
            same meaning as 'Re:'.
        iii) Leading strings such as 'FW:' are treated as new subjects.

        Parameters
        ----------
        per_address_field :

        Returns
        -------
        A dictionary of the form {'subject1': index of message, 'subject2': ...}
        is returned. If per_address_field is specified, the subjects are sorted
        into the domain or localpart from which they originate.
        """
        if df is None:
            indices = get_index_of_msgs_with_subject(self.df, return_boolmask=True)
            _df = self.df.loc[indices]
        else:
            indices = get_index_of_msgs_with_subject(df, return_boolmask=True)
            _df = df.loc[indices]
        # find index of thread root and its subject line
        indices = []
        for index, row in _df.iterrows():
            subject_not_reply = []
            for rl in reply_labels:
                if rl not in row.subject[:25]:
                    subject_not_reply.append(True)
                else:
                    subject_not_reply.append(False)
            if all(subject_not_reply):
                indices.append(index)
        _df = self.df.loc[indices]
        subjects = {value: key for key, value in _df["subject"].to_dict().items()}
        # sort into address field
        if per_address_field:
            generator = ListservMailList.iterator_name_localpart_domain(
                _df["from"].values
            )
            if "domain" in per_address_field:
                domains = [domain for _, _, domain in generator]
                dics = {do: {} for do in list(set(domains)) if do is not None}
                for do, sb in zip(domains, list(subjects.keys())):
                    if do is not None:
                        dics[do][sb] = subjects[sb]
            elif "localpart" in per_address_field:
                localparts = [localpart for _, localpart, _ in generator]
                dics = {lp: {} for lp in list(set(localparts)) if lp is not None}
                for lp, sb in zip(localparts, list(subjects.keys())):
                    if lp is not None:
                        dics[lp][sb] = subjects[sb]
            subjects = dics
        return subjects

    def get_threadsrootcount(
        self,
        per_address_field: Optional[str] = None,
        per_year: bool = False,
    ) -> Union[int, dict]:
        """
        Identify number conversation threads in mailing list.

        Parameters
        ----------
        per_address_field: Aggregate results for each address field, which can
            be, e.g., `from`, `send-to`, `received-by`.
        per_year : Aggregate results for each year.
        """
        if per_year:
            dics = {}
            period_of_activity = self.period_of_activity()
            years = [dt.year for dt in period_of_activity]
            years = np.arange(min(years), max(years) + 1)

            for year in years:
                mlist_fi = self.crop_by_year(year)
                subjects = self.get_threadsroot(per_address_field, df=mlist_fi.df)
                if per_address_field:
                    dics[year] = {key: len(values) for key, values in subjects.items()}
                else:
                    dics[year] = len(subjects)
            return dics
        else:
            subjects = self.get_threadsroot(per_address_field)
            if per_address_field:
                return {key: len(values) for key, values in subjects.items()}
            else:
                return len(subjects)

    def get_messagescount(
        self,
        header_fields: Optional[List[str]] = None,
        per_address_field: Optional[str] = None,
        per_year: bool = False,
    ) -> dict:
        """
        Parameters
        ----------
        header_fields : Indicate which Email header field to process
            (e.g. 'from', 'reply-to', 'comments-to'). For a listserv
            mailing list the most representative header fields of
            senders and receivers are 'from' and 'comments-to' respectively.
        per_year : Aggregate results for each year.
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
                            return_msg_counts=True,
                        )
                    elif "localpart" in per_address_field:
                        res = mlist_fi.get_localparts(
                            [header_field],
                            per_domain=False,
                            return_msg_counts=True,
                        )
                    dics[header_field][int(year)] = {
                        label: count for label, count in res[header_field]
                    }
            return dics
        if header_fields:
            if "domain" in per_address_field:
                res = self.get_domains(
                    header_fields,
                    return_msg_counts=True,
                )
            elif "localpart" in per_address_field:
                res = self.get_localparts(
                    header_fields,
                    per_domain=False,
                    return_msg_counts=True,
                )
            dics = {}
            for header_field, _res in res.items():
                dics[header_field] = {label: count for label, count in _res}
            return dics
        else:
            return len(self.df.index.values)

    def get_messagescount_per_timezone(
        self,
        percentage: bool = False,
    ) -> Dict[str, int]:
        """
        Get contribution of messages per time zone.

        Parameters
        ----------
        percentage : Whether to return count of messages percentage w.r.t. total.
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

    def get_sender_receiver_dict(
        self,
        address_field: str = "domain",
        entity_in_focus: Optional[list] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> Dict:
        """
        Parameters
        ----------
        address_field :
        entity_in_focus : This can a list of domain names or localparts. If such
            a list is provided, the creaed dictionary will only contain their
            information.

        Returns
        -------
        Nested dictionary with first layer the 'from' domain keys and
        the second layer the 'comments-to' domain keys with the
        integer indicating the number of messages between them.
        """
        # remove messages that have been written to the whole group without
        # addressing anyone specifically.
        if df is None:
            df = self.df
        df = df[["from", "comments-to"]].dropna()
        if address_field == "domain":
            domains = self.get_domains(header_fields=["from", "comments-to"])
            domains = list(set(domains["from"] + domains["comments-to"]))
            dic = {do: {} for do in domains}
        if address_field == "localpart":
            localparts = self.get_localparts(header_fields=["from", "comments-to"])
            localparts = list(set(localparts["from"] + localparts["comments-to"]))
            dic = {lp: {} for lp in localparts}
        # loop through messages
        for index, row in df.iterrows():
            (
                _,
                f_localpart,
                f_domain,
            ) = ListservMailList.get_name_localpart_domain(row["from"])
            if f_domain is None:
                continue

            ct_generator = ListservMailList.iterator_name_localpart_domain(
                [df.loc[index]["comments-to"]]
            )
            for _, ct_localpart, ct_domain in ct_generator:
                if ct_domain is None:
                    continue
                if address_field == "domain":
                    # counting the messages
                    dic = self.add_weight_to_edge(dic, f_domain, ct_domain)
                if address_field == "localpart":
                    # counting the messages
                    dic = self.add_weight_to_edge(dic, f_localpart, ct_localpart)

        if entity_in_focus is not None:
            dic = self.crop_dic_to_entity_in_focus(dic)

        return dic

    def crop_dic_to_entity_in_focus(self, dic: dict, entity_in_focus: list) -> dict:
        """
        Parameters
        ----------
        entity_in_focus : This can a list of domain names or localparts.
        """
        dic_eif = {}
        for sender, receivers in dic.items():
            for receiver, nr_msgs in receivers.items():
                if sender in entity_in_focus:
                    if sender not in dic_eif.keys():
                        dic_eif[sender] = {}
                    dic_eif[sender][receiver] = nr_msgs

                if receiver in entity_in_focus:
                    if sender not in dic_eif.keys():
                        dic_eif[sender] = {}
                    dic_eif[sender][receiver] = nr_msgs
        return dic_eif

    def add_weight_to_edge(self, dic: dict, key1: str, key2: str) -> dict:
        """
        Parameters
        ----------
        dic :
        key1 :
        key2 :
        """
        # counting the messages
        if key2 not in dic[key1].keys():
            dic[key1][key2] = 1
        else:
            dic[key1][key2] += 1
        return dic

    def create_sender_receiver_digraph(
        self,
        nw: Optional[dict] = None,
        entity_in_focus: Optional[list] = None,
        node_attributes: Optional[Dict[str, list]] = None,
    ):
        """
        Create directed graph from messaging network created with
        ListservMailList.get_sender_receiver_dict().

        Parameters
        ----------
        nw : dictionary created with self.get_sender_receiver_dict()
        entity_in_focus : This can be a list of domain names or localparts. If
            such a list is provided, the creaed di-graph will only focus on their
            relations.
        node_attributes: A dictionary with
        """
        if nw is None:
            nw = self.get_sender_receiver_dict(
                address_field="domain",
                entity_in_focus=entity_in_focus,
            )
        # initialise graph
        DG = nx.DiGraph()
        if entity_in_focus:
            # create nodes
            nodes = []
            for sender, _dic in nw.items():
                if sender in entity_in_focus:
                    nodes.append(sender)
                for receiver in _dic.keys():
                    if receiver in entity_in_focus:
                        nodes.append(receiver)
            nodes = list(set(nodes))
            [DG.add_node(node) for node in nodes]
            # create edges
            for sender, receivers in nw.items():
                if sender not in entity_in_focus:
                    continue
                for receiver, nr_msgs in receivers.items():
                    DG.add_edge(sender, receiver, weight=nr_msgs)
        else:
            # create nodes
            nodes = []
            for sender, _dic in nw.items():
                nodes.append(sender)
                for receiver in _dic.keys():
                    nodes.append(receiver)
            nodes = list(set(nodes))
            [DG.add_node(node) for node in nodes]
            # create edges
            for sender, receivers in nw.items():
                for receiver, nr_msgs in receivers.items():
                    DG.add_edge(sender, receiver, weight=nr_msgs)
        if node_attributes is not None:
            node_attribute_value = {}
            for index, node in enumerate(DG.nodes):
                if node in node_attributes["node_name"]:
                    node_attr = node_attributes["node_attribute"][
                        node_attributes["node_name"].index(node)
                    ]
                    node_attribute_value[node] = node_attr
                else:
                    node_attribute_value[node] = "Unkown"
            nx.set_node_attributes(DG, node_attribute_value, name="node_attribute")
        # attach directed graph to class
        self.dg = DG

    def get_graph_prop_per_domain_per_year(
        self,
        years: Optional[tuple] = None,
        func=nx.betweenness_centrality,
        **args,
    ) -> dict:
        """
        Parameters
        ----------
        years :
        func :
        """
        if years is None:
            period_of_activity = self.period_of_activity()
            years = [dt.year for dt in period_of_activity]
            years = np.arange(min(years), max(years) + 1)

        dic_evol = {}
        for year in years:
            mlist_fi = self.crop_by_year(year)
            nw = self.get_sender_receiver_dict(
                address_field="domain",
                df=mlist_fi.df,
            )
            mlist_fi.create_sender_receiver_digraph(nw=nw)

            adj = func(mlist_fi.dg, **args)

            labels = list(adj.keys())
            values = np.array(list(adj.values()))

            for lab, val in zip(labels, values):
                if lab not in list(dic_evol.keys()):
                    dic_evol[lab] = {
                        "year": [year],
                        func.__name__: [val],
                    }
                else:
                    dic_evol[lab]["year"].append(year)
                    dic_evol[lab][func.__name__].append(val)
        return dic_evol


class ListservMailListDomain:
    """
    Parameters
    ----------
    name
        The of whom the mail list domain is (e.g. 3GPP, IEEE, ...)
    filedsc
        The file description of the mail list domain
    lists
        A list containing the mailing lists as `ListservMailList` types

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
    ) -> "ListservMailListDomain":
        filepaths = get_paths_to_files_in_directory(directorypath, filedsc)
        if len(filepaths) > 0:
            ListservMailListDomainWarning("No files found fitting the description")
        for count, filepath in enumerate(filepaths):
            name = filepath.split("/")[-1].split(".")[0]
            mlist = ListservMailList.from_mbox(name, filepath).df
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
        dic_mlis = {key: len(list(set(value))) for key, value in dic_mlis.items()}
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
