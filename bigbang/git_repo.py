from datetime import datetime
from time import mktime

import git
import networkx as nx
import numpy as np
import pandas as pd
from git import *
from git import Repo

from config.config import CONFIG

from . import utils
from .entity_resolution import entity_resolve

ALL_ATTRIBUTES = (
    CONFIG.all_attributes
)  # ["HEXSHA", "Committer Name", "Committer Email", "Commit Message", "Time", "Parent Commit", "Touched File"]


def cache_fixer(r):
    """Adds info from row to graph."""
    r["Touched File"] = [x.strip() for x in r["Touched File"][1:-1].split(",")]
    r["Time"] = pd.to_datetime(r["Time"])
    return r


class GitRepo(object):
    """
    Store a git repository given the address to that repo relative to this file.

    It returns the data in many forms.
    """

    def __init__(self, name, url=None, attribs=ALL_ATTRIBUTES, cache=None):
        """
        Index a Pandas DataFrame object by time.

        That stores the raw form of the repo's commit data as a table.

        Each row in this table  is a commit.

        And each column represents an attribute of that commit:
        (eg.: time, message, commiter name, committer email, commit hexsha).
        """

        self._commit_data = None
        self.url = url
        self.repo = None
        self.name = name

        if cache is None:
            self.repo = Repo(url)
            self.populate_data(ALL_ATTRIBUTES)
        else:
            cache = cache.apply(cache_fixer, axis=1)
            cache.set_index(cache["Time"])
            self._commit_data = cache

            missing = list()
            cols = self.commit_data.columns
            for attr in attribs:
                if attr not in cols and str(attr) not in cols:
                    missing.append(attr)

            if len(missing) > 0:
                print(
                    (
                        "There were "
                        + str(len(missing))
                        + " missing attributes: "
                    )
                )
                print(missing)

        if "Committer Name" in attribs and "Committer Email" in attribs:
            self._commit_data["Person-ID"] = None
            self._commit_data = self._commit_data.apply(
                lambda row: entity_resolve(
                    row, "Committer Email", "Committer Name"
                ),
                axis=1,
            )

    def gen_data(self, repo, raw):
        """Generate data to repo."""

        if not repo.active_branch.is_valid():
            print(("Found an empty repo: " + str(self.name)))
            return
        first = repo.commit()
        commit = first
        firstHexSha = first.hexsha
        generator = git.Commit.iter_items(repo, firstHexSha)

        if "Touched File" in raw:
            print(
                "WARNING: Currently going through file diffs. This will take a very long time (1 minute per 3000 commits.) We suggest using a small repository."
            )
        for commit in generator:
            try:
                if "Touched File" in raw:
                    diff_list = list()
                    for diff in commit.diff(commit.parents[0]):
                        if diff.b_blob:
                            diff_list.append(diff.b_blob.path)
                        else:
                            diff_list.append(diff.a_blob.path)
                    raw["Touched File"].append(diff_list)

                if "Committer Name" in raw:
                    raw["Committer Name"].append(commit.committer.name)

                if "Committer Email" in raw:
                    raw["Committer Email"].append(commit.committer.email)

                if "Commit Message" in raw:
                    raw["Commit Message"].append(commit.message)

                if (
                    "Time" in raw or True
                ):  # TODO: For now, we always ask for the time
                    raw["Time"].append(
                        pd.to_datetime(commit.committed_date, unit="s")
                    )

                if "Parent Commit" in raw:
                    raw["Parent Commit"].append(
                        [par.hexsha for par in commit.parents]
                    )

                if "HEXSHA" in raw:
                    raw["HEXSHA"].append(commit.hexsha)
            except LookupError:
                print("failed to add a commit because of an encoding error")

    def populate_data(self, attribs=ALL_ATTRIBUTES):
        """Populate data."""
        raw = dict()
        for attrib in attribs:
            raw[attrib] = list()
        repo = self.repo
        self.gen_data(repo, raw)
        print((type(raw["Time"])))

        time_index = pd.DatetimeIndex(raw["Time"]).to_period("H")
        time_index = utils.add_freq(time_index, freq=None)
        self._commit_data = pd.DataFrame(raw, index = time_index);

    def by_committer(self):
        """Return commit data grouped by commiter."""
        return self.commit_data.groupby("Committer Name").size().order()

    def commits_per_day(self):
        """Return commits grouped by day."""
        ans = self.commit_data.groupby(self.commit_data.index).size()
        ans = ans.resample("D", how=np.sum)
        return ans

    def commits_per_week(self):
        """Return commits grouped by week."""
        ans = self.commits_per_day()
        ans = ans.resample("W", how=np.sum)
        return ans

    def commits_per_day_full(self):
        """Return commits grouped by day and by commiter."""
        ans = self.commit_data.groupby(
            [self.commit_data.index, "Committer Name"]
        ).size()
        return ans

    @property
    def commit_data(self):
        """Return commit data."""
        return self._commit_data

    def commits_for_committer(self, committer_name):
        """Return commits for committer given the commiter name."""
        full_info = self.commit_data

        df = full_info.loc[full_info["Committer Name"] == committer_name]
        df = df.groupby([df.index]).size()
        df = df.resample("D", how=np.sum, axis=0)

        return df

    def merge_with_repo(self, other):
        """Append commit to a repo."""
        # TODO: What if commits have the same time?
        self._commit_data = self.commit_data.append(other.commit_data)


class MultiGitRepo(GitRepo):
    """Repos must have a "Repo Name" column."""

    def __init__(self, repos, attribs=ALL_ATTRIBUTES):
        self._commit_data = repos[0].commit_data.copy(deep=True)
        for i in range(1, len(repos)):
            self.merge_with_repo(repos[i])
