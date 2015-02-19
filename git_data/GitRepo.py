from git import *
import git
import pandas as pd
import numpy as np
from time import mktime
from datetime import datetime

"""
Class that stores an instance of a git repository given the address to that
repo relative to this file. It returns the data in multiple useful forms.
"""
class GitRepo:

	""" A pandas DataFrame object indexed by time that stores
	the raw form of the repo's commit data as a table where 
	each row is a commit and each col represents an attribute 
	of that commit (time, message, commiter name, committer email,
	commit hexsha)
	"""

	def __init__(self, url):
		self._commit_data = None;
		self.url = url;
		self.repo = Repo(url)
		self.populate_data()




	def populate_data(self):
		raw = dict()
		raw["HEXSHA"] = list()
		raw["Committer Name"] = list()
		raw["Committer Email"] = list()
		raw["Commit Message"] = list()
		raw["Time"] = list()
		raw["Parent Commit"] = list()



		repo = self.repo
		first = repo.commit()
		commit = first
		firstHexSha = first.hexsha;
		generator = git.Commit.iter_items(repo, firstHexSha);
		
		for commit in generator:
			try: 
				raw["Committer Name"].append(commit.committer.name)
				raw["Committer Email"].append(commit.committer.email)
				raw["Commit Message"].append(commit.message)
				raw["Time"].append(pd.to_datetime(commit.committed_date, unit = "s"));
				raw["Parent Commit"].append([par.hexsha for par in commit.parents])
				raw["HEXSHA"].append(commit.hexsha)
				
			except LookupError:
				print("failed to add a commit because of an encoding error")

		time_index = pd.DatetimeIndex(raw["Time"], periods = 24, freq = "H")
		self._commit_data = pd.DataFrame(raw, index = time_index);

	def by_committer(self):
		return self.commit_data.groupby('Committer Name').size().order()

	def commits_per_day(self):
		ans = self.commit_data.groupby(self.commit_data.index).size()
		ans = ans.resample("D", how=np.sum)
		return ans;

	def commits_per_week(self):
		ans = self.commits_per_day();
		ans = ans.resample("W", how=np.sum)
		return ans;

	def commits_per_day_full(self):
		ans = self.commit_data.groupby([self.commit_data.index, "Committer Name" ]).size()
		return ans;

	@property
	def commit_data(self):
		return self._commit_data;

	def commits_for_committer(self, committer_name):
		full_info = self.commit_data
		time_index = pd.DatetimeIndex(self.commit_data["Time"], periods = 24, freq = "H");

		df = full_info.loc[full_info["Committer Name"] == committer_name]
		df = df.groupby([df.index]).size()
		df = df.resample("D", how = np.sum, axis = 0)

		return df


