import sys
import getopt

import bigbang.analysis.repo_loader as loader


def main(argv):
    update = False

    if "--update" in argv:
        update = True
    try:
        opts, args = getopt.getopt(argv, "u:f:g:", ["update"])
    except getopt.GetoptError as e:
        print("GetoptError: %s" % (e))
        sys.exit(2)

    for opt, arg in opts:
        print((opt, arg))
        if opt == "-f":
            load_by_file(arg, update)
            sys.exit()
        elif opt == "-u":
            load_by_URL(arg, update)
        elif opt == "-g":
            load_by_org(arg, update)


def load_by_file(filePath, update=False):
    urls = open(filePath, "r")

    for url in urls:
        loader.get_repo(url, "remote", update)


def load_by_URL(url, update=False):
    loader.get_repo(url, "remote", update)


def load_by_org(org_name, update=False):
    loader.get_org_repos(org_name)


if __name__ == "__main__":
    main(sys.argv[1:])
