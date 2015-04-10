import sys;
import getopt

import bigbang.repo_loader as loader


def main(argv):
    update = False

    if "--update" in argv:
        update = True
    try:
        opts, args = getopt.getopt(argv, "u:f:", ["update"])
    except getopt.GetoptError as e:
        print 'GetoptError: %s' % (e)
        sys.exit(2)

    
    for opt, arg in opts:
        if opt == '-f':
            load_by_file(arg, update);
            sys.exit()
        elif opt == '-u':
            load_by_URL(arg, update);

def load_by_file(filePath, update = False):
    urls = open(filePath, "r");

    for url in urls:
        loader.get_repo(url, "remote", update);

def load_by_URL(url, update = False):
    loader.get_repo(url, "remote", update);


if __name__ == "__main__":
    main(sys.argv[1:])
