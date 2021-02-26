import ast
import fnmatch
import json
import os
import re
import subprocess
import sys

import networkx as nx
import pandas as pd
import requests
from IPython.nbconvert import PythonExporter
from IPython.nbformat import current as nbformat

from config.config import CONFIG

from .git_repo import GitRepo, MultiGitRepo

repoLocation = CONFIG.repo_path
examplesLocation = CONFIG.urls_path
nameRegex = re.compile(r"([^/]*)\.git$")
fileRegex = re.compile(r".*\/(.*)")


class RepoLoaderWarning(BaseException):
    """Base class for Archive class specific exceptions"""

    pass


def repo_already_exists(filepath):
    return os.path.exists(filepath)


def url_to_name(url):
    """
    Converts a github url (e.g. https://github.com/sbenthall/bigbang.git) to
    a human-readable name (bigbang) by looking at the word between the last "/" and ".git".
    """
    url = url.replace("\n","")
    name = nameRegex.search(url).group(1)
    return name


def name_to_filepath(name):
    """
    Converts a name of a repo to its filepath.
    Currently, these go to ../archives/sample_git_repos/{name}/
    """
    newLoc = repoLocation + name
    return newLoc


def filepath_to_name(filepath):
    """
    Converts a filepath (../archives/sample_git_repos/{name}) to a name.
    Note that this will fail if the filepath ends in a "/". It must end
    in the name of the folder.
    Thus, it should be ../archives/sample_git_repos/{name} not
    ../archives/sample_git_repos/{name}/
    """
    name = fileRegex.search(filepath).group(1)
    return name


def create_graph(dic):
    """
    Converts a dictionary of dependencies into a  NetworkX DiGraph.
    """
    G = nx.DiGraph()
    for f in dic:
        for dependency in dic[f]:
            G.add_edge(f, dependency)
    return G


def get_files(filepath):
    """
    Returns a list of the Python files in a directory, and
    converts IPython notebooks into Python source code and
    includes them with the Python files.
    """
    os.chdir(filepath)
    files = []
    for root, dirnames, filenames in os.walk("."):
        for filename in fnmatch.filter(filenames, "*.py"):
            files.append(os.path.join(root, filename))

        for filename in fnmatch.filter(filenames, "*.ipynb"):
            try:
                with open(filename) as fh:
                    nb = nbformat.reads_json(fh.read())
                    export_path = filename.replace(".ipynb", ".py")
                    exporter = PythonExporter()
                    source, meta = exporter.from_notebook_node(nb)

                with open(export_path, "w+") as fh:
                    fh.writelines(source)
                files.append()
            except Exception as e:
                raise RepoLoaderWarning(
                    f"May have issues with JSON encoding. The error message is: {e}"
                )
    return files


def get_dependency_network(filepath):
    """
    Given a directory, collects all Python and IPython files and
    uses the Python AST to create a dictionary of dependencies from them.
    Returns the dependencies converted into a NetworkX graph.
    """
    files = get_files(filepath)
    dependencies = {}
    for file in set(files):
        tree = ast.parse(file)
        for node in tree.getChildren()[1].nodes:
            if isinstance(node, tree.Import):
                if file in dependencies:
                    dependencies[file].append(node.names[0][0])
                else:
                    dependencies[file] = [node.names[0][0]]

            elif isinstance(node, tree.From):
                if file in dependencies:
                    dependencies[file].append(
                        node.modname + "/" + node.names[0][0]
                    )
    return create_graph(dependencies)


def get_repo(repo_in, in_type="name", update=False):
    """
    Takes three different options for type:
        - remote: basically a git url
        - name (default): a name like 'scipy' which the method can expand to a url
        - local: a filepath to a file on the local system
            (basically an existing git directory on this computer)
    This returns an initialized GitRepo object with its data and name already loaded.
    """
    # Input is name
    if in_type == "name":
        filepath = name_to_filepath(repo_in)
        ans = None
        if not update:
            ans = get_cache(repo_in)
        if ans is not None:
            return ans
        print(("Checking for " + str(repo_in) + " at " + str(filepath)))
        ans = get_repo(filepath, "local", update)

        if isinstance(ans, GitRepo):
            # We cache it hopefully???
            ans.commit_data.to_csv(
                cache_path(repo_in), sep="\t", encoding="utf-8"
            )
        else:
            print("We failed to find a local copy of this repo")
        return ans

    # Input is a local file
    if in_type == "local":
        if repo_already_exists(repo_in):
            name = filepath_to_name(repo_in)
            return GitRepo(url=repo_in, name=name)
        else:
            print(("Invalid filepath: " + repo_in))
            return None

    if in_type == "remote":
        name = url_to_name(repo_in)
        filepath = name_to_filepath(name)
        if not repo_already_exists(filepath):
            print("Cloning the repo from remote")
            fetch_repo(repo_in)
        return get_repo(name, "name", update)

    else:
        print("Invalid input")  # TODO: Clarify this error
        return None


def fetch_repo(url):
    """
    Takes in a git url and uses shell commands
    to clone the git repo into sample_git_repos/

    TODO: We shouldn't use this with shell=True because of security concerns.
    """
    # TODO: We are repeatedly calculating name and filepath
    url = url.replace("\n", "")
    name = url_to_name(url)
    newLoc = name_to_filepath(name)
    command = ["git " + "clone " + url + " " + newLoc]
    subprocess.call(command, shell=True)


def cache_path(name):
    """
    Takes in a name (bigbang)
    Returns where its cached file should be (../sample_git_repos/bigbang_backup.csv)
    """
    return repoLocation + str(name) + "_backup.csv"


def get_cache(name):
    """
    Takes in a name (bigbang)
    Returns a GitRepo object containing the cache data if the cache exists
    Returns None otherwise.
    """
    filepath = cache_path(name)
    if os.path.exists(filepath):
        c = pd.read_csv(filepath, sep="\t", encoding="utf-8")
        fp = name_to_filepath(name)
        ans = GitRepo(name=name, url=fp, cache=c)
        return ans
    return None


def get_multi_repo(repo_names=None, repos=None):
    """
    As of now, this only accepts names/repos, not local urls
    TODO: This could be optimized
    """
    if repos is None:
        repos = list()
        for name in repo_names:
            repo = get_repo(name, in_type="name")
            repos.append(repo)

    for repo in repos:
        repo.commit_data["Repo Name"] = repo.name

    ans = MultiGitRepo(repos)
    return ans


def load_org_repos(org_name):
    """
    fetches a list of all repos in an organization from github
    and gathers their URL's (of the form *.git)
    It dumps these into ../examples/{org_name}_urls.txt
    """
    github_url = "https://api.github.com/orgs/" + org_name + "/repos"
    r = requests.get(github_url)
    data = r.json()
    urls = []
    for repo in data:
        if "git_url" in repo:
            urls.append(repo["git_url"])
    if len(urls) == 0:
        print(("Found no repos in group: " + str(org_name)))
        return None
    else:
        addr = examplesLocation + str(org_name) + "_urls.txt"
        f = open(addr, "w")
        f.write("\n".join(urls))
        print(("Wrote git urls to " + addr))
        return urls


def get_org_repos(org_name):
    """
    Checks to see if we have the urls for a given org
    If we don't, it fetches them.
    Once we do, it returns a list of GitRepo objects from the urls.
    """
    addr = examplesLocation + str(org_name) + "_urls.txt"
    urls = None
    if not os.path.isfile(addr):
        urls = load_org_repos(org_name)
    else:
        urls = open(addr, "r")
    ans = list()
    for url in urls:
        ans.append(get_repo(url, "remote"))

    return ans


def get_org_multirepo(org_name):
    repos = get_org_repos(org_name)
    ans = get_multi_repo(repos=repos)
    return ans
