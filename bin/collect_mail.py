import argparse
import getopt
import logging
import sys
from argparse import RawTextHelpFormatter

import bigbang.ingress.mailman as mailman

parser = argparse.ArgumentParser(
    formatter_class=RawTextHelpFormatter,
    description=r"""
    Collects files from public mailing list archives.

    Please include either a url of a mailman web archive or the path to a file with
    a linebreak-separated list of such urls.

    For example:

    python bin/collect_mail.py -u http://mail.python.org/pipermail/scipy-dev/

    or

    python bin/collect_mail.py -f examples/urls.txt

    """,
)
parser.add_argument("-u", type=str, help="URL of mailman archive")

parser.add_argument(
    "-f", type=str, help="Path of a file with linebreak-seperated list of URLs"
)

parser.add_argument(
    "--archives",
    type=str,
    help="Path to a specified directory for storing downloaded mail archives",
)

parser.add_argument("--notes", type=str, help="Notes to record regarding provenance")

args = parser.parse_args()

logging.basicConfig(level=logging.INFO)


def main(args):
    notes = None
    if args.notes:
        notes = args.notes

    if args.u:
        if args.archives:
            mailman.collect_from_url(args.u, archive_dir=args.archives, notes=notes)
        else:
            mailman.collect_from_url(args.u, notes=notes)
        sys.exit()
    elif args.f:
        if args.archives:
            mailman.collect_from_file(args.f, archive_dir=args.archives, notes=notes)
        else:
            mailman.collect_from_file(args.f, notes=notes)


if __name__ == "__main__":
    main(args)
