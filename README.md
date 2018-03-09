# BigBang

BigBang is a toolkit for studying communications data from collaborative
projects. It currently supports analyzing mailing lists from Sourceforge,
Mailman, or [.mbox][mbox] files.

[mbox]: http://tools.ietf.org/html/rfc4155

## Installation

You can use [Anaconda](http://continuum.io/downloads). This will also install
the `conda` package management system, which you can use to complete
installation. 

Install Anaconda (with Python version 2.7) from http://continuum.io/downloads

(If you choose not to use Anaconda, you will most probably run into issues with versioning in Python.)

Ensure to add the Conda installation directory to your path during installation. 

Run the following commands:

```bash
git clone https://github.com/nllz/bigbang.git
conda create -n bigbang python=2.7
cd bigbang
bash conda-setup.sh
```

### pip installation

Run the following commands:

```bash
git clone https://github.com/sbenthall/bigbang.git
# optionally create a new virtualenv here
pip install -r requirements.txt
python setup.py develop
```

## Usage

There are serveral IPython notebooks in the `examples/` directory of this
repository. To open them and begin exploring, run the following commands in the
root directory of this repository:

```bash
source activate bigbang
ipython notebook examples/
```

### Collecting from Mailman

BigBang comes with a script for collecting files from public Mailman web
archives. An example of this is the
[scipy-dev](http://mail.python.org/pipermail/scipy-dev/) mailing list page. To
collect the archives of the scipy-dev mailing list, run the following command
from the root directory of this repository:

```bash
python bin/collect_mail.py -u http://mail.python.org/pipermail/scipy-dev/
```

You can also give this command a file with several urls, one per line. One of these is provided in the `examples/` directory.

```bash
python bin/collect_mail.py -f examples/urls.txt
```

Once the data has been collected, BigBang has functions to support analysis.

# Git Information

A new branch of BigBang is collecting git commit information for projects. We can analyze a project using both its mail and git information to answer new questions about development.

## Collecting Git Information

After the git repositories have been cloned locally, you will be able to start analyzing them. To do this, you will need a GitRepo object, which is a convenient wrapper which does the work of extracting and generating git information and storing it internally in a pandas dataframe. You can then use this GitRepo object's methods to gain access to the large pandas dataframe.

There are many ways to generate a GitRepo object for a repository, using RepoLoader:
* Bash scripts (in the bigbang directory):
    * single url `python bin/collect_git.py -u https://github.com/scipy/scipy.git`
    * file of urls `python bin/collect_git.py -f examples/git_urls.txt`
    * Github organization name `python bin/collect_git.py -g glass-bead-labs`
* Single Repo:
    * remote `get_repo("https://github.com/sbenthall/bigbang.git", in_type = "remote" )`
    * local `get_repo("~/urap/bigbang/archives/sample_git_repos/bigbang",  in_type = "local" )`
    * name `get_repo("bigbang", in_type = "name")`
* Multiple Repos:
   * With repo names: `get_multi_repo(repo_names=["bigbang","django"])`
   * With repo objects: `get_multi_repo(repos=[{list of existing GitRepo objects}]`
   * With Github Organization names `get_org_multirepo("glass-bead-labs")`

### Repo Locations
As of now, repos are clones into `archives/sample_git_repos/{repo_name}`. Their caches are stored at `archives/sample_git_repos/{repo_name}_backup.csv`.

### Caches
Caches are stored at `archives/sample_git_repos/{repo_name}_backup.csv`. They are the dumped `.csv` files of a GitRepo object's `commit_data` attribute, which is a pandas dataframe of all commit information. We can initialize a GitRepo object by feeding the cache's Pandas dataframe into the GitRepo init function. However, the init function will need to do some processing before it can use the cache as its commit data. It needs to convert the `"Touched File"` attribute of the cache dataframe from unicode `"[file1, file2, file3]"` to an actual list `["file1", "file2", "file3"]`. It will also need to convert the time index of the cache from string to datetime.

### Bash Scripts

Run the following commands while in the bigbang directory. The repo information will go into the default repo location.

```bash
python bin/collect_git.py -u https://github.com/scipy/scipy.git
```

You can also give this command a file with several urls, one per line. One of these is provided in the `examples/` directory.

```bash
python bin/collect_git.py -f examples/git_urls.txt
```

This command will load all of the repos of a github organization. Make sure that the name is exactly as it appears on Github.

```bash
python bin/collect_git.py -g glass-bead-labs
```

### Single Repos
Here, we can load in three ways. We can use a github url, a local path to a repo, or the name of a repo. All of these return a `GitRepo` object. Here is an example, with explanations below.

```python
from bigbang import repo_loader # The file that handles most loading

repo = repo_loader.get_repo("https://github.com/sbenthall/bigbang.git", in_type = "remote" )
# repo = repo_loader.get_repo("../",  in_type = "local" ) # I commented this out because it may take too long
repo = repo_loader.get_repo("bigbang", in_type = "name")

repo.commit_data # The pandas df of commit data
```

#### Remote
A remote call to `get_repo` will extract the repo's name from its git url. Thus, `https://github.com/sbenthall/bigbang.git` will yield `bigbang` as its name. It will check if the repo already exists. If it doesn't it will send a shell command to clone the remote repository to `archives/sample_git_repos/{repo_name}`. It will then return `get_repo({name}, in_type="name")`. Before returning, however, it will cache the GitRepo object at `archives/sample_git_repos/{repo_name}_backup.csv` to make loading faster the next time.

#### Local
A local call is the simplest. It will first extract the repo name from the filepath. Thus, `~/urap/bigbang/archives/sample_git_repos/bigbang` will yield `bigbang`. It will check to see if a git repo exists at the given address. If it does, it will initialize a GitPython object, which only needs a name and a filepath to a Git repo. Note that this option does not check or create a cache.

### Name
This is the preferred and easiest way to load a git repository. It works under the assumptions above about where a git repo and its cache should be stored. It will check to see if a cache exists. If it does, then it will load a GitPython object using that cache.

If a cache is not found, then the function constructs a filepath from the name, using the above rule about where repo locations. It will pass off the function to `get_repo(filepath, in_type="local")`. Before returning the answer, it will cache the result.

### MultiRepos
These are the ways we can get MultiGitRepo objects. MultiGitRepo objects are GitRepos that were created with a list of GitRepos. Basically, a MultiGitRepo's `commit_data` contains the commit_data from all of its GitRepos. The only difference is that each entry has an extra attribute, `Repo Name` that tells us which Repo that commit is initially from. Here are some examples, with explanations below. Note that the examples below will not work if you don't have an internet connection, and may take some time to process. The first call may also fail if you do not have all of the repositories

```python
from bigbang import repo_loader # The file that handles most loading

## Using GitHub API
multirepo = repo_loader.get_org_multirepo("glass-bead-labs")

## List of repo names
multirepo = repo_loader.get_multi_repo(repo_names = ["bigbang","bead.glass"])

## List of actual repos
repo1 = repo_loader.get_repo("bigbang", in_type="name")
repo2 = repo_loader.get_repo("bead.glass", in_type="name")
multirepo = repo_loader.get_multi_repo(repos = [repo1, repo2])

multirepo.commit_data # The pandas df of commit data
```

#### List of Repos / List of Repo Names (`get_multi_repo`)
This is rather simple. We can call the `get_multi_repo` method with either a list of repo names `["bigbang", "django", "scipy"]` or a list of actual GitRepo objects. This returns us the merged MultiGitRepo. Please note that this will not work if a local clone / cache of the repos does not exist for every repo name (e.g. if you ask for `["bigbang", "django", "scipy"]`, you must already have a local copy of those in your sample_git_repos directory.

#### Github Organization's Repos (`get_org_multirepo`)
This is more useful to us. We can use this method to get a MultiGitRepo that contains the information from every repo in a Github Organization. This requires that we input the organization's name *exactly* as it appears on Github (edX, glass-bead-labs, codeforamerica, etc.)

It will look for `examples/{org_name}_urls.txt`, which should be a file that contains all of the git urls of the projects that belong to that organization. If this file doesn't yet exist, it will make a call to the Github API. This requires a stable internet connection, and it may randomly stall on requests that do not time out.

The function will then use the list of git urls and the `get_repo` method to get each repo. It will use this list of repos to create a MultiGitRepo object, using `get_multi_repo`.




## Community

If you are interested in participating in BigBang development or would like support from the core development team, please subscribe to [BigBang-user mailing list](https://lists.ghserv.net/mailman/listinfo/bigbang-dev) and let us know what your suggestions, questions, requests and comments are. 

## License

AGPL-3.0, see LICENSE for its text. This license may be changed at any time according to the principles of the project [Governance](https://github.com/datactive/bigbang/wiki/Governance).
