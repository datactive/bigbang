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

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "u:f:")
    except getopt.GetoptError as e:
        print 'GetoptError: %s' % (e)
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-u':
            loadByFile(arg);
            sys.exit()
        elif opt == '-f':
            loadByURL(arg);

def loadByFile(filePath):
    urls = open(filePath, "r");
    repoInfos = dict();

    for url in urls:
        loadRepoIntoDict(url, repoInfos);

    json.dump(repoInfos, LOCALS, indent=4)

def loadRepoIntoDict(url, repoInfo):
    url = url.replace("\n", "");
    name = nameRegex.search(url).group(1);
    newLoc = repoLocation + "/" + name
    command = ["git " + "clone " +  url + " " + newLoc];
    subprocess.call(command, shell = True);
    repoInfo[name] = newLoc;

def loadByURL(url):
    repoInfos = dict();

    loadRepoIntoDict(url, repoInfos);

    json.dump(repoInfos, LOCALS, indent=4)

if __name__ == "__main__":
    main(sys.argv[1:])
