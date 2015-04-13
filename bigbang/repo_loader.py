from git_repo import GitRepo, MultiGitRepo
import json;
import os;
import re;
import subprocess;
import sys;
import pandas as pd

repoLocation = os.path.dirname(os.path.realpath(__file__))
last_index = repoLocation.rfind("/")
repoLocation = repoLocation[0:last_index] + "/archives/sample_git_repos/"

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
def get_multi_repo(repo_names):
    repos = list()
    for name in repo_names:
        repo = get_repo(name, in_type = "name")
        repo.commit_data["Repo Name"] = name;
        repos.append(repo);

    ans = MultiGitRepo(repos);
    return ans