import re;
import subprocess;
import json;

URLS = open("git_urls.txt", "r");
LOCALS = open("git_locals.json","w");
localRepos = dict();
repoLocation = "sample_git_repos";
nameRegex = re.compile("([a-z]*)(\\.git$)")

for url in URLS:
	url = url.replace("\n", "");
	name = nameRegex.search(url).group(1);
	newLoc = repoLocation + "/" + name
	command = ["git " + "clone " +  url + " " + newLoc];
	subprocess.call(command, shell = True);
	localRepos[name] = newLoc;

json.dump(localRepos, LOCALS, indent=4)