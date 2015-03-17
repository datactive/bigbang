import re;
import subprocess;
import json;
import getopt
import sys;
import os;

repoLocation = "./git_data/sample_git_repos";
nameRegex = re.compile("([a-z]*)(\\.git$)")
print(os.path.dirname(os.getcwd()))
LOCALS = open("./git_data/git_locals.json", "w")


def url_to_name(url):
    url = url.replace("\n", "");
    name = nameRegex.search(url).group(1);
    return name;

def name_to_filepath(name):
    newLoc = repoLocation + name
    return newLoc

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "u:f:")
    except getopt.GetoptError as e:
        print 'GetoptError: %s' % (e)
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-f':
            loadByFile(arg);
            sys.exit()
        elif opt == '-u':
            loadByURL(arg);

def loadByFile(filePath):
    urls = open(filePath, "r");
    repoInfos = dict();

    for url in urls:
        loadRepoIntoDict(url, repoInfos);

    json.dump(repoInfos, LOCALS, indent=4)

def loadRepoIntoDict(url, repoInfo):

    name = url_to_name(url);
    newLoc = name_to_filepath(name);

    command = ["git " + "clone " +  url + " " + newLoc];
    subprocess.call(command, shell = True);
    repoInfo[name] = newLoc;

def loadByURL(url):
    repoInfos = dict();

    loadRepoIntoDict(url, repoInfos);

    json.dump(repoInfos, LOCALS, indent=4)

if __name__ == "__main__":
    main(sys.argv[1:])
