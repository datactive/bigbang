from git_repo import GitRepo, MultiGitRepo
import json;
import os;
import re;
import subprocess;
import sys;
import pandas as pd
import requests

repoLocation = os.path.dirname(os.path.realpath(__file__))
last_index = repoLocation.rfind("/")
repoLocation = repoLocation[0:last_index] + "/archives/sample_git_repos/"
examplesLocation = repoLocation[0:last_index] + "/examples/"
nameRegex = re.compile("([^/]*)(\\.git$)")
fileRegex = re.compile(".*\/(.*)")

def repo_already_exists(filepath):
    return os.path.exists(filepath);

def url_to_name(url):
    url = url.replace("\n", "");
    name = nameRegex.search(url).group(1);
    return name;

def name_to_filepath(name):
    newLoc = repoLocation + name
    return newLoc

def filepath_to_name(filepath):
    name = fileRegex.search(filepath).group(1);
    print(name);
    return name;


"""
Takes three different options for type:
    'remote'		: basically a git url
    'name' (default): a name like 'scipy' which the method can expand to a url
    'local'			: a filepath to a file on the local system (basically an existing git directory on this computer)
"""
def get_repo(repo_in, in_type='name', update = False):
    
    s_df = pd.DataFrame();
    
    if in_type == 'name':
        filepath = name_to_filepath(repo_in)
        ans = None;
        if not update:
            print("Checking if cached")
            ans = get_cache(repo_in);
        if ans is not None:
            return ans;
        print("Checking for " + str(repo_in) + " at " + str(filepath));
        ans = get_repo(filepath, 'local', update);

        if isinstance(ans, GitRepo):
            ans.commit_data.to_csv(cache_path(repo_in), sep='\t', encoding='utf-8') # We cache it hopefully???
        else:
            print("We failed to find a local copy of this repo")
        return ans;

    if in_type == 'local':
        if repo_already_exists(repo_in):
            name = filepath_to_name(repo_in);
            return GitRepo(url=repo_in, name=name);
        else:
            print("Invalid filepath: " + repo_in);
            return None;

    if in_type == 'remote':

        name = url_to_name(repo_in);
        filepath = name_to_filepath(name);
        if not repo_already_exists(filepath):
            print("Gloning the repo from remote")
            fetch_repo(repo_in);
        return get_repo(name, 'name', update);

    else:
    	print("Invalid input") # TODO: Clarify this error
    	return None


def fetch_repo(url):
    # TODO: We are repeatedly calculating name and filepath
    url = url.replace("\n", "");
    name = url_to_name(url);
    newLoc = name_to_filepath(name);
    command = ["git " + "clone " +  url + " " + newLoc];
    subprocess.call(command, shell = True);

def cache_path(name):
    return repoLocation + str(name) + "_backup.csv"

def get_cache(name):
    filepath = cache_path(name);
    if os.path.exists(filepath):
        c = pd.read_csv(filepath, sep='\t', encoding='utf-8');
        fp = name_to_filepath(name);
        ans = GitRepo(name=name, url=fp, cache=c);
        return ans;
    return None;

"""
As of now, this only accepts names, not local urls
TODO: This could be optimized
"""
def get_multi_repo(repo_names=None, repos=None):
    if repos is None:
        repos = list()
        for name in repo_names:
            repo = get_repo(name, in_type = "name")
            repos.append(repo);

    for repo in repos:
        repo.commit_data["Repo Name"] = repo.name;

    ans = MultiGitRepo(repos);
    return ans

"""
fetches a list of all repos in an organization from github
and gathers their URL's (of the form *.git)
It dumps these into ../examples/{org_name}_urls.txt
"""
def load_org_repos(org_name):
    github_url = "https://api.github.com/orgs/" + org_name + "/repos"
    r = requests.get(github_url)

    data = r.json()

    urls = []
    for repo in data:
        if "git_url" in repo:
            urls.append(repo["git_url"])

    if len(urls) == 0:
        print("Found no repos in group: " + str(org_name))
        return None
    else:
        addr = examplesLocation + str(org_name) + "_urls.txt"
        f = open(addr, 'w')
        f.write("\n".join(urls))
        print("Wrote git urls to " + addr)
        return urls


def get_org_repos(org_name):
    addr = examplesLocation + str(org_name) + "_urls.txt"
    urls = None
    if not os.path.isfile(addr):
        urls = load_org_repos(org_name);
    else:
        urls = open(addr, "r")

    ans = list()
    for url in urls:
        ans.append(get_repo(url, "remote"))

    return ans;
