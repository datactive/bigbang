
from GitRepo import GitRepo
import json;
import os;
import re;
import subprocess;
import sys;

repoLocation = os.path.dirname(os.path.realpath(__file__))
print(repoLocation);
last_index = repoLocation.rfind("/")
repoLocation = repoLocation[0:last_index] + "/git_data/sample_git_repos/"
nameRegex = re.compile("([a-z]*)(\\.git$)")


def repo_already_exists(filepath):
    return os.path.exists(filepath);

def url_to_name(url):
    url = url.replace("\n", "");
    name = nameRegex.search(url).group(1);
    return name;

def name_to_filepath(name):
    newLoc = repoLocation + name
    return newLoc


"""
Takes three different options for type:
    'remote'		: basically a git url
    'name' (default): a name like 'scipy' which the method can expand to a url
    'local'			: a filepath to a file on the local system (basically an existing git directory on this computer)
"""
def get_repo(repo_in, in_type='name'):
    if in_type == 'name':
        filepath = name_to_filepath(repo_in)

        print("Checking for " + str(repo_in) + " at " + str(filepath));
        return get_repo(filepath, 'local');
         
    if in_type == 'local':
        if repo_already_exists(repo_in):
            return GitRepo(repo_in);
        else:
            print("Invalid filepath: " + repo_in);
            return False;

    if in_type == 'remote':

        filepath = name_to_filepath(url_to_name(repo_in));
        if not repo_already_exists:
            fetch_repo(repo_in);
        return get_repo(filepath, 'local');

    else:
    	print("Invalid input") # TODO: Clarify this error
    	return False

def fetch_repo(url):
    # TODO: We are repeatedly calculating name and filepath
    name = url_to_name(url);
    newLoc = name_to_filepath(name);
    command = ["git " + "clone " +  url + " " + newLoc];
    subprocess.call(command, shell = True);
    repoInfo[name] = newLoc;


"""https://github.com/scipy/scipy.git
https://github.com/npm/npm.git"""