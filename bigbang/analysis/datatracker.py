"""
Scripts for processing data from the IETF DataTracker
"""

from bigbang.config import CONFIG

import bigbang.datasets.organizations as bdo

from datetime import date, datetime, timezone
from dateutil.parser import *
import json as json

import pandas as pd
import re


from ietfdata.datatracker import *
from ietfdata.datatracker_ext import *
from ietfdata.rfcindex import *

import sys

# adding the cache configuration path here
cache_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), CONFIG.ietfdata_cache_path)
)
sys.path.insert(0, cache_path)
print(f"cache path: {cache_path}")

dt = DataTrackerExt()
ri = RFCIndex()

odf = bdo.load_data()


def rfc_author_data(rfc, normalize=True):
    record = {}

    record["title"] = rfc.title
    record["draft"] = rfc.draft
    record["date"] = rfc.date()
    record["wg"] = rfc.wg
    record["docid"] = rfc.doc_id

    draft = None
    if rfc.draft is not None:
        draft = dt.document_from_draft(rfc.draft[:-3])
        if draft is None:
            draft = dt.document_from_rfc(rfc.doc_id)
    else:
        draft = dt.document_from_rfc(rfc.doc_id)
    if draft is not None:
        record["draft-date"] = draft.time
        record["authors"] = []

        for author in dt.document_authors(draft):
            person = dt.person(author.person)

            affiliation = author.affiliation

            if normalize:
                affiliation = normalize_affiliation(affiliation)

            if affiliation == "":
                affiliation = person.name

            author = {
                "id": person.id,
                "country": author.country,
                "name": person.name,
                "affiliation": affiliation,
            }

            record["authors"].append(author)

        record["revision"] = draft.rev

        return record

    else:
        return None


def authorship_from_rfc_data(rfc_data):
    records = []

    for author in rfc_data["authors"]:
        author_record = author.copy()

        author_record["draft"] = rfc_data["draft"]
        author_record["title"] = rfc_data["title"]
        author_record["date"] = rfc_data["date"].strftime(
            "%Y-%m-%d"
        )  # format this to string!
        author_record["wg"] = rfc_data["wg"]
        author_record["docid"] = rfc_data["docid"]

        records.append(author_record)

    return records


def rfc_authors_from_working_group(acr):
    """
    Get a dataframe of all authors of RFCs published
    by the working group.
    """
    author_records = []

    for rfc in ri.rfcs(wg=acr):
        rfc_data = rfc_author_data(rfc)
        if rfc_data is not None:
            authorship = authorship_from_rfc_data(rfc_data)
            author_records.extend(authorship)
        else:
            print(f"No rfc data for {rfc}")

    else:
        # IRTF groups don't have their RFCs listed in the same way.
        wg = dt.group_from_acronym(acr)
        rfcs = dt.documents(group=wg, doctype=dt.document_type_from_slug("rfc"))

        for rfc_doc in rfcs:
            rfc = ri.rfc(rfc_doc.name.upper())

            rfc_data = rfc_author_data(rfc)
            if rfc_data is not None:
                authorship = authorship_from_rfc_data(rfc_data)
                author_records.extend(authorship)

    # if len(author_records) > 0 :
    df = pd.DataFrame.from_records(author_records)

    return df


def draft_authors_from_working_group(acr):
    """
    Get a dataframe of all authors of drafts published
    by the working group.

    NOTE: In a change in late 2023 or early 2024, the IETD DataTracker
    API changed, and rfc documents are no longer listed with their
    drafts as submissions. This version of the query is now deprecated.

    """

    # identify group
    g = dt.group_from_acronym(acr)

    records = []
    # get drafts.
    # filter by rfc status here?
    for draft in dt.documents(
        group=g,
        doctype=dt.document_type_from_slug("rfc"),  # "draft"
    ):  # status argument
        # interested in all submissions, or just the most recent?

        if draft.rfc:
            submissions = [dt.submission(sub_url) for sub_url in draft.submissions]
            submissions = sorted(
                submissions, key=lambda s: s.submission_date, reverse=True
            )

            print(f"len(submissions) == {len(submissions)}")
            if len(submissions) > 0:
                latest = submissions[0]

                authors_text = latest.authors

                try:
                    at = authors_text.replace("'", '"')
                    at = at.replace("None", "null")
                    authors = json.loads(at)
                except Exception as e:
                    print(e)
                    authors = [{"raw_text": authors_text}]

                for a in authors:
                    a["submission_date"] = latest.submission_date
                    a["draft_uri"] = latest.draft.uri
                    a["title"] = latest.title
                    a["rfc"] = int(draft.rfc)

                records.append(authors)

    records = sum(records, [])
    records = sorted(records, key=lambda x: x["rfc"])

    df = pd.DataFrame.from_records(records)

    return df


em_re = "/api/v1/person/email/([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7})/"


def email_from_uri(email_uri):
    m = re.match(em_re, email_uri)

    return m.group(1) if m else None


dt = DataTracker()


def get_group_histories(wg_name):
    """
    For a working group name, get the group history objects
    associated with that working group.
    """
    wg = dt.group_from_acronym(wg_name)
    group_histories = dt.group_histories(group=wg)

    group_role_histories = [
        dt.group_role_histories(
            group=grp_hist,
            name=dt.role_name(RoleNameURI(uri="/api/v1/name/rolename/chair/")),
        )
        for grp_hist in group_histories
    ]

    return group_histories, group_role_histories


def leadership_ranges(group_acronym):
    """
    For a working group acronym,
    get the data about the changes to the Chair role
    in that working group history.
    """
    wg = dt.group_from_acronym(group_acronym)
    group_histories = dt.group_histories(group=wg)

    gh = list(group_histories)

    gh_chair_records = [
        [
            {
                "datetime_max": h.time,
                "datetime_min": h.time,
                # "email": email_from_uri(r.email.uri),
                "person_uri": r.person.uri,
                "name": dt.person(r.person).name,
                # "biography": dt.person(r.person).biography,
            }
            for r in list(
                dt.group_role_histories(
                    group=h,
                    name=dt.role_name(RoleNameURI(uri="/api/v1/name/rolename/chair/")),
                )
            )
        ]
        for h in gh
    ]

    gh_chair_records = sum(gh_chair_records, [])
    ghcr_df = pd.DataFrame.from_records(gh_chair_records)

    agged = ghcr_df.groupby(["name", "person_uri"]).agg(  # "email", "biography"
        {"datetime_min": "min", "datetime_max": "max"}
    )

    ## Minimum time is the first record.
    # agged["datetime_min"].replace({ghcr_df["datetime_min"].min(): None}, inplace=True)

    ## TODO: replace with current time
    agged["datetime_max"].replace(
        {ghcr_df["datetime_max"].max(): datetime.now(timezone.utc)}, inplace=True
    )
    agged = agged.sort_values(by="datetime_max")

    return ghcr_df, agged


def normalize_affiliation(affil):
    """

    Probably should be somewhere else.
    """
    affil = affil.strip()

    lookup = bdo.lookup_normalized(affil, odf)

    if lookup is not None:
        affil = lookup

    affil = affil.strip()  # in case there's an error there

    return affil
