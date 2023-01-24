import bigbang.analysis.process as process
import bigbang.analysis.utils as utils
import dataclasses
from ietfdata.datatracker import DataTracker, MeetingTypeURI
from ietfdata.datatracker_ext import DataTrackerExt
import pandas as pd


def name_email_affil_relations_from_IETF_attendance(
    meeting_range=[106, 107, 108], threshold=None
):
    """

    Extract and infer from IETF attendance records relations between full names, email address, and affiliations.

    In the returned dataframes, each row represents a relation between two of these forms of entity,
    along with the maximum and minimum date associated with it in the data.

    Two forms of inference are used when generating these relational tables:

     - Missing values in time are filled forward, then filled backward
     - TODO: Affiliations are ran through the entity resolution script to reduce them to a 'cannonical form'

    Parameters
    ------------

    meeting_range: list of ints
        The numbers of the IETF meetings to use for source data

    threshold: float
        Defaults to None. If not None, activate entity resolution on the affiliations.
        Threshold value is used for the entity resolution.


    Returns
    -----------

    rel_name_affil: pandas.DataFrame

    rel_email_affil: pandas.DataFrame

    rel_name_email: pandas.DataFrame


    """
    datatracker = DataTracker()
    dt = DataTrackerExt()  # initialize, for all meeting registration downloads

    meetings = datatracker.meetings(
        meeting_type=datatracker.meeting_type(
            MeetingTypeURI("/api/v1/name/meetingtypename/ietf/")
        )
    )
    full_ietf_meetings = list(meetings)

    meeting_attendees_df = pd.DataFrame()
    ietf_meetings = []
    for meeting in full_ietf_meetings:
        meetingd = dataclasses.asdict(meeting)
        meetingd["meeting_obj"] = meeting
        meetingd["num"] = int(meeting.number)
        ietf_meetings.append(meetingd)

    for meeting in ietf_meetings:
        if (
            meeting["num"] in meeting_range
        ):  # can filter here by the meetings to analyze
            registrations = dt.meeting_registrations(meeting=meeting["meeting_obj"])
            df = pd.DataFrame.from_records(
                [dataclasses.asdict(x) for x in list(registrations)]
            )
            df["num"] = meeting["num"]
            df["date"] = meeting["date"]
            df["domain"] = df["email"].apply(utils.extract_domain)
            full_name = df["first_name"] + " " + df["last_name"]
            df["full_name"] = full_name
            meeting_attendees_df = meeting_attendees_df.append(df)

    ind_affiliation = meeting_attendees_df[
        ["full_name", "affiliation", "email", "domain", "date"]
    ]

    if threshold is not None:
        org_names = ind_affiliation["affiliation"].dropna().value_counts()
        ents = process.resolve_entities(
            org_names, process.containment_distance, threshold=0.15
        )

        replacements = {}
        for r in [{name: ent for name in ents[ent]} for ent in ents]:
            replacements.update(r)

        ind_affiliation.loc[:, "affiliation"] = ind_affiliation["affiliation"].apply(
            lambda x: replacements[x]
        )  # , axis = 1)

    # full_name / affiliation
    name_affil_dates = (
        ind_affiliation.pivot_table(
            index="date",
            columns="full_name",
            values="affiliation",
            aggfunc="first",
        )
        .fillna(method="ffill")
        .fillna(method="bfill")
    )

    long_name_affils = name_affil_dates.reset_index().melt(
        id_vars=["date"], value_name="affiliation"
    )

    rel_name_affil = (
        long_name_affils.groupby(["full_name", "affiliation"])["date"]
        .agg(["min", "max"])
        .reset_index()
        .rename({"min": "min_date", "max": "max_date"}, axis=1)
    )

    # email / affiliation
    email_affil_dates = (
        ind_affiliation.pivot_table(
            index="date",
            columns="email",
            values="affiliation",
            aggfunc="first",
        )
        .fillna(method="ffill")
        .fillna(method="bfill")
    )

    long_email_affils = email_affil_dates.reset_index().melt(
        id_vars=["date"], value_name="affiliation"
    )

    rel_email_affil = (
        long_email_affils.groupby(["email", "affiliation"])["date"]
        .agg(["min", "max"])
        .reset_index()
        .rename({"min": "min_date", "max": "max_date"}, axis=1)
    )

    # name / email
    name_email_dates = (
        ind_affiliation.pivot_table(
            index="date", columns="full_name", values="email", aggfunc="first"
        )
        .fillna(method="ffill")
        .fillna(method="bfill")
    )

    long_name_email = name_email_dates.reset_index().melt(
        id_vars=["date"], value_name="email"
    )

    rel_name_email = (
        long_name_email.groupby(["full_name", "email"])["date"]
        .agg(["min", "max"])
        .reset_index()
        .rename({"min": "min_date", "max": "max_date"}, axis=1)
    )

    return rel_name_affil, rel_email_affil, rel_name_email
