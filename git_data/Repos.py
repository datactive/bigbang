
from GitRepo import GitRepo
import json;

NBPATH = "../git_data/"
LOCALS = open(NBPATH + "git_locals.json");


repo_urls = json.load(LOCALS);

def get_repo(name):
	if name in repo_urls:
		repo = GitRepo("../" + repo_urls[name])
		return repo
	else:
		return None;


"""https://github.com/scipy/scipy.git
https://github.com/npm/npm.git"""