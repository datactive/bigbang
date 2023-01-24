import sys
import os
import os.path
import getopt
import bigbang.ingress.mailman as mailman
import bigbang.archive
import pandas as pd
import numpy as np
import logging
import argparse
import enlighten
import gc

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    description=r"""
Calculates the tenure and total messages sent by each person.

Provide the path to a directory of archives, containing subdirectories for each mailing list.

For example:

python bin/tenure.py --archives ../archives

With the `--combine` parameter, gathers and merges together the values in all subdirectory CSV files into a single combined tenure CSV file in the archives directory.
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
    help="Overwrite existing -tenure.csv files; by default this is false and directories with an existing file are skipped.",
)
parser.add_argument(
    "-c",
    "--combine",
    action="store_true",
    help="Aggregate values from all subdirectories with existing tenure files into a single CSV.",
)


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("chardet.charsetprober").setLevel(logging.WARNING)
logging.getLogger("chardet.universaldetector").setLevel(logging.WARNING)


def earliest(s):
    """
    Finds the earliest date from the columns of an activity dataframe that show messages sent per date.

    Takes a pandas.Series where the columns are the dates (and a couple of calculated columns which will be ignored for the purposes of the calculation) and the cells are the number of messages sent on each date.
    """
    # these standalone earliest, latest and total_messages methods aren't currently in use, but they'll be useful again soon.
    just_dates = s.drop(
        ["Earliest Date", "Latest Date", "Total Messages", "Tenure"],
        errors="ignore",
    )

    earliest = None

    if "Earliest Date" in s.index:
        if pd.notna(s["Earliest Date"]):
            earliest = s["Earliest Date"]

    # limited to all the dates where the value is greater than 0
    # then take the array of the dates and calculate the min value
    earliest_date = just_dates.loc[just_dates > 0].index.min()

    if earliest is not None:
        if earliest < earliest_date:
            return earliest
    return earliest_date


def latest(s):
    """
    Finds the latest date from the columns of an activity dataframe that show messages sent per date.

    Takes a pandas.Series where the columns are the dates (and a couple of calculated columns which will be ignored for the purposes of the calculation) and the cells are the number of messages sent on each date.
    """
    just_dates = s.drop(
        ["Earliest Date", "Latest Date", "Total Messages", "Tenure"],
        errors="ignore",
    )

    latest = None

    if "Latest Date" in s.index:
        if pd.notna(s["Latest Date"]):
            latest = s["Latest Date"]

    # limited to all the dates where the value is greater than 0
    # then take the array of the dates and calculate the max value
    latest_date = just_dates.loc[just_dates > 0].index.max()

    if latest is not None:
        if latest > latest_date:
            return latest
    return latest_date


def total_messages(s):
    """
    Finds the total number of messages sent from an activity dataframe that show messages sent per date.

    Takes a pandas.Series where the columns are the dates (and a couple of calculated columns which will be ignored for the purposes of the calculation) and the cells are the number of messages sent on each date. This does not ignore but instead adds up an existing 'Total Messages' column.
    """
    just_dates = s.drop(["Earliest Date", "Latest Date", "Tenure"], errors="ignore")
    return just_dates.sum()


def main(args):
    subdirectories = next(os.walk(args.archives))[1]

    if args.combine:
        combined_out_path = os.path.join(args.archives, "combined-tenure.csv")

        combined_df = None
        combined_lists = (
            []
        )  # list of all the mailing lists included in the combined dataframe
        for subdirectory in subdirectories:
            in_path = os.path.join(
                args.archives, subdirectory, ("%s-tenure.csv" % subdirectory)
            )
            if os.path.isfile(in_path):
                in_df = pd.read_csv(in_path, encoding="utf-8", index_col=0)
                if combined_df is not None:
                    both = pd.concat([in_df, combined_df])
                    combined_df = both.groupby(both.index).agg(
                        {
                            "Earliest Date": np.min,
                            "Latest Date": np.max,
                            "Total Messages": np.sum,
                        }
                    )
                    combined_lists.append(
                        subdirectory
                    )  # add subdirectory name to combined_lists
                    logging.info("Merged tenure from %s" % subdirectory)
                else:
                    combined_df = in_df
                    combined_lists = [subdirectory]
                    logging.info("Started with tenure from %s" % subdirectory)
            else:
                logging.warning("No tenure file in %s" % subdirectory)

        with open(combined_out_path, "w") as f:
            combined_df.to_csv(f, encoding="utf-8")
            logging.info("Completed combined tenure frame output.")
            logging.info("Subdirectories included: %s" % ",".join(combined_lists))
    else:
        manager = enlighten.get_manager()
        progress = manager.counter(
            total=len(subdirectories), desc="Lists", unit="lists"
        )
        for subdirectory in subdirectories:
            logging.info("Processing archives in %s" % subdirectory)

            out_path = os.path.join(
                args.archives, subdirectory, ("%s-tenure.csv" % subdirectory)
            )

            if not args.force:
                if os.path.isfile(out_path):  # if file already exists, skip
                    progress.update()
                    continue
            try:
                logging.debug("Opening list archives in %s", subdirectory)
                archives = mailman.open_list_archives(subdirectory, args.archives)

                logging.debug("Creating archive")
                archive = bigbang.archive.Archive(archives)

                logging.debug("Creating activity frame from archive")
                activity = archive.get_activity()
                del archive
                gc.collect()

                logging.debug("Transposing activity frame")
                person_activity = activity.T

                logging.debug("Iterating for tenure calculations")
                earliest_column, latest_column, total_column = [], [], []
                i = 0
                for _, s in person_activity.iterrows():
                    i = i + 1
                    if i % 100 == 0:
                        logging.debug("checkpoint: %d", i)
                        gc.collect()
                    earliest_date = s.loc[s > 0].index.min()
                    latest_date = s.loc[s > 0].index.max()
                    total_messages = s.sum()
                    earliest_column.append(earliest_date)
                    latest_column.append(latest_date)
                    total_column.append(total_messages)
                index_column = person_activity.index
                del person_activity

                # delete the other columns
                logging.debug("Create new frame from columns")
                tenure_frame = pd.DataFrame(
                    index=index_column,
                    data={
                        "Earliest Date": earliest_column,
                        "Latest Date": latest_column,
                        "Total Messages": total_column,
                    },
                )

                logging.debug("Writing tenure frame to file")
                with open(out_path, "w") as f:
                    tenure_frame.to_csv(f, encoding="utf-8")
                    logging.info("Completed tenure frame export for %s" % subdirectory)
            except Exception:
                logging.warning(
                    ("Failed to produce tenure frame export for %s." % subdirectory),
                    exc_info=True,
                )
            progress.update()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)
