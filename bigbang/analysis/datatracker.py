"""
Scripts for processing data from the IETF DataTracker
"""

from ietfdata.datatracker import *
from ietfdata.datatracker_ext import *
from dateutil.parser import *

import pandas as pd
import re

dt = DataTrackerExt()

em_re = "/api/v1/person/email/([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7})/"


def email_from_uri(email_uri):
    m = re.match(em_re, email_uri)

    return m.group(1) if m else None


dt = DataTracker(use_cache=True)


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
            name=dt.role_name(RoleNameURI("/api/v1/name/rolename/chair/")),
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
                "email": email_from_uri(r.email.uri),
                "person_uri": r.person.uri,
                "name": dt.person(r.person).name,
                "biography": dt.person(r.person).biography,
            }
            for r in list(
                dt.group_role_histories(
                    group=h,
                    name=dt.role_name(RoleNameURI("/api/v1/name/rolename/chair/")),
                )
            )
        ]
        for h in gh
    ]

    gh_chair_records = sum(gh_chair_records, [])
    ghcr_df = pd.DataFrame.from_records(gh_chair_records)

    agged = ghcr_df.groupby(["name", "person_uri", "email", "biography"]).agg(
        {"datetime_min": "min", "datetime_max": "max"}
    )

    agged["datetime_min"].replace({ghcr_df["datetime_min"].min(): None}, inplace=True)

    agged["datetime_max"].replace({ghcr_df["datetime_max"].max(): None}, inplace=True)

    return ghcr_df, agged
