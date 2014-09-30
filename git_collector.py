from git import *
import pandas as pd
import numpy as np
from time import mktime
from datetime import datetime

repo = Repo(""".""")
assert(repo.bare == False);

commits = repo.commits()
notYetPandas = dict()

"""
Properties We Want:
Commit Time
Commit Committer's Name
Commit Committer's Email
Commit Message
Commit Hash
"""

notYetPandas["Committer Name"] = [commit.committer.name for commit in commits];
notYetPandas["Committer Email"] = [commit.committer.email for commit in commits];
notYetPandas["Time"] = [datetime(*commit.committed_date[:6]) for commit in commits];
notYetPandas["Commit Message"] = [commit.message for commit in commits];


dataFrame = pd.DataFrame(notYetPandas);
