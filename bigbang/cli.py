import os
import pandas as pd

from ietfdata.datatracker import *

import click
from .ingress import mailman
from .analysis import repo_loader

from .config import CONFIG


@click.group()
def main():
    """BigBang CLI tools"""


# collect mail


@main.command()
@click.option("--url", "url", help="URL of mailman archive")
@click.option(
    "--file", "file", help="Path of a file with linebreak-seperated list of URLs"
)
@click.option(
    "--archives",
    "archives",
    default="./archives",
    show_default=True,
    help="Path to a specified directory for storing downloaded mail archives",
)
@click.option("--notes", "notes", help="Notes to record regarding provenance")
def collect_mail(url, file, archives, notes):
    """Collects files from public mailman mailing list archives"""
    if url:
        mailman.collect_from_url(url, archive_dir=archives, notes=notes)
    elif file:
        mailman.collect_from_file(file, archive_dir=archives, notes=notes)
    else:
        print("Either --url or --file must be set")


# collect git


@main.command()
@click.option("--url", "url", required=True, help="URL of the git repo")
@click.option("--update", default=False, show_default=True, help="Update the git repo")
def collect_git_from_url(url, update):
    """Load git data from a repo URL"""
    repo_loader.get_repo(url, "remote", update)


@main.command()
@click.option(
    "--path", "path", required=True, help="Path of the file full of git repo URLs"
)
@click.option("--update", default=False, show_default=True, help="Update the git repo")
def collect_git_from_file_of_urls(path, update):
    """Load git data from repo URLs listed in a file"""
    with open(path, "r") as f:
        for line in f.readlines():
            url = line.strip()
            repo_loader.get_repo(url, "remote", update)


@main.command()
@click.option("--org-name", "org_name", required=True, help="GitHub organization name")
def collect_git_from_github_org(org_name):
    """Load git data from repos in a GitHub organization"""
    repo_loader.get_org_repos(org_name)


# collect draft metadata


def collect_draft_metadata_setup_path(wg):
    if not os.path.exists(CONFIG.datatracker_path):
        os.makedirs(CONFIG.datatracker_path)

    wg_path = os.path.join(CONFIG.datatracker_path, wg)

    if not os.path.exists(wg_path):
        os.makedirs(wg_path)

    return wg_path


def collect_draft_metadata_extract_data(doc, dt):
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


@main.command()
@click.option("--working-group", "wg", required=True, help="IETF working group acronym")
def collect_draft_metadata(wg):
    """Collects files from public mailing list archives"""
    wg_path = collect_draft_metadata_setup_path(wg)

    ## initialize datatracker
    dt = DataTracker()

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

    collection = [
        sub_data
        for draft in drafts
        for sub_data in collect_draft_metadata_extract_data(draft, dt)
    ]

    draft_df = pd.DataFrame(collection)
    draft_df.to_csv(fn)
