import sys;
import getopt

import bigbang.repo_loader as loader

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "u:f:")
    except getopt.GetoptError as e:
        print 'GetoptError: %s' % (e)
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-f':
            load_by_file(arg);
            sys.exit()
        elif opt == '-u':
            load_by_URL(arg);

def load_by_file(filePath):
    urls = open(filePath, "r");

    for url in urls:
        loader.get_repo(url, "remote");

def load_by_URL(url):
    loader.get_repo(url, "remote");


if __name__ == "__main__":
    main(sys.argv[1:])
