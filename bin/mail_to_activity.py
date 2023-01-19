import sys
import os
import os.path
import getopt
import bigbang.ingress.mailman as mailman
import bigbang.archive
import pandas as pd
import logging
import argparse

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    description=r"""
Creates activity frames from mailing list archives.

Provide the path to a directory of archives, containing subdirectories for each mailing list.

For example:

python bin/mail_to_activity.py --archives ../archives

""",
)

parser.add_argument(
    "--archives",
    type=str,
    help="Path to a specified directory of downloaded mail archives",
    required=True,
)

parser.add_argument(
    "-f",
    "--force",
    action="store_true",
    help="Overwrite existing -activity.csv files; by default this is false and directories with an existing file are skipped.",
)

args = parser.parse_args()

logging.basicConfig(level=logging.INFO)


def main(args):
    subdirectories = next(os.walk(args.archives))[1]

    for subdirectory in subdirectories:
        logging.info("Processing archives in %s" % subdirectory)

        if not args.force:
            out_path = os.path.join(
                args.archives, subdirectory, ("%s-activity.csv" % subdirectory)
            )
            if os.path.isfile(out_path):  # if file already exists, skip
                continue
        try:
            archives = mailman.open_list_archives(subdirectory, args.archives)
            activity = bigbang.archive.Archive(archives).get_activity()
            # sum the message count, rather than by date, to prevent enormous, sparse files
            activity = pd.DataFrame(activity.sum(0), columns=["Message Count"])

            out_path = os.path.join(
                args.archives, subdirectory, ("%s-activity.csv" % subdirectory)
            )

            with open(out_path, "w") as f:
                activity.to_csv(f, encoding="utf-8")
        except Exception:
            logging.warning(
                ("Failed to produce activity frame export for %s." % subdirectory),
                exc_info=True,
            )


if __name__ == "__main__":
    main(args)
