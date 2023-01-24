from bigbang.config import CONFIG
from ietfdata.datatracker import *
import os
import pandas as pd

## set up directory for storing metadata files


def setup_path(wg):
    if not os.path.exists(CONFIG.datatracker_path):
        os.makedirs(CONFIG.datatracker_path)

    wg_path = os.path.join(CONFIG.datatracker_path, wg)

    if not os.path.exists(wg_path):
        os.makedirs(wg_path)

    return wg_path


## metadata extraction function


def extract_data(doc, dt):
    data = {}
    data["title"] = doc.title

    ## TODO: do this in only one loop over authors
    data["person"] = [
        dt.person(doc_author.person) for doc_author in dt.document_authors(doc)
    ]

    data["affiliation"] = [
        doc_author.affiliation for doc_author in dt.document_authors(doc)
    ]
    data["group-acronym"] = dt.group(doc.group).acronym
    data["type"] = doc.type.uri

    # use submissions for dates
    sub_data = [
        {"date": dt.submission(sub_url).document_date} for sub_url in doc.submissions
    ]

    for sd in sub_data:
        sd.update(data)

    return sub_data


def collect_drafts(wg):
    wg_path = setup_path(wg)

    ## initialize datatracker
    dt = DataTracker(cache_dir=Path("cache"))

    group = dt.group_from_acronym(wg)

    if group is None:
        raise Exception(f"Group {wg} not found in datatracker")

    ## Begin execution
    print("Collecting drafts from datatracker")

    # This returns a generator
    drafts = dt.documents(
        group=group,
        doctype=dt.document_type(DocumentTypeURI("/api/v1/name/doctypename/draft/")),
    )

    fn = os.path.join(wg_path, "draft_metadata.csv")

    collection = [sub_data for draft in drafts for sub_data in extract_data(draft, dt)]

    draft_df = pd.DataFrame(collection)
    draft_df.to_csv(fn)


import argparse
from argparse import RawTextHelpFormatter
import logging

parser = argparse.ArgumentParser(
    formatter_class=RawTextHelpFormatter,
    description=r"""
Collects files from public mailing list archives.

Please include an IETF working group acronym 

For example:

python bin/datatracker.py -w httpbis

""",
)
parser.add_argument("-w", type=str, help="IETF working group acronym")

args = parser.parse_args()

logging.basicConfig(level=logging.INFO)


def main(args):
    if args.w:
        collect_drafts(args.w)
    else:
        raise Exception("No working group given")


if __name__ == "__main__":
    main(args)
