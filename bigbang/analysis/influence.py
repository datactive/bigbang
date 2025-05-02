from bigbang.archive import Archive, open_list_archives

import bigbang.parse as parse
import bigbang.analysis.utils as utils

import email.header

import matplotlib.pyplot as plt
import pandas as pd

import os
import subprocess

from bigbang.datasets import domains, organizations

"""
Processing of mailing list data to support an analysis
of actor-influence, where actors are understood to be at
the affilation/organization level.
"""

dd = domains.load_data()
odf = organizations.load_data()

good_categories = ["company", "academic", "sdo"]  # not "generic"


def lookup_stakeholder_by_domain(domain):
    """
    For an email domain, use the organization data provided in BigBang
    to look up the organization name associate with that email domain.

    TODO: reconcile with bigbang.datasets.organizations.lookup_normalized
    """

    search = odf["email domain names"].apply(lambda dn: domain in str(dn))

    orgs = odf[search]

    top_orgs = orgs[orgs["subsidiary of / alias of"].isna()]

    if top_orgs.shape[0] > 0:
        return top_orgs["name"].iloc[0]
    elif orgs.shape[0] > 0:
        # look up the domain of the parent organization
        parent_name = orgs["subsidiary of / alias of"].iloc[0]

        search_up = odf[odf["name"] == parent_name]

        if search_up.shape[0] > 0:
            return lookup_stakeholder_by_domain(search_up["email domain names"].iloc[0])
        else:
            print(
                f"{domain} is neither top level org nor has a parent org -- should never happen"
            )
            return domain
    else:
        # domain isn't in the database
        return domain


def normalize_senders_by_domain(row):
    try:
        if dd.loc[row["domain"]]["category"] in good_categories:
            cleaned = lookup_stakeholder_by_domain(row["domain"])
        else:
            cleaned = parse.clean_from(row["From"])

    except Exception as e:
        try:
            print(f"Exception in normalizing sender by domain: {e}")
            # doing this by exception handling is messy.
            cleaned = parse.clean_from(row["From"])
            print(row["From"], " --> ", cleaned)
        except Exception as e:
            print(e, f"{row['From']} not cleaned")
            cleaned = row["From"]

    if " via Datatracker" in cleaned:
        cleaned = cleaned.replace(" via Datatracker", "")

    return cleaned


def is_affiliation(domain):
    try:
        if dd.loc[domain]["category"] in good_categories:
            return lookup_stakeholder_by_domain(domain)
        else:
            return "Unaffiliated"
    except Exception as e:
        print(e)
        return "Unaffiliated"


def augment(arx):
    """
    Add to an email archive's data three new columns: an email addres,
    an email domain, and the 'category' of the sender, which may be an
    organization name, 'Unaffiliated', or a cleaned version of the email's
    From field.
    """
    arx.data["email"] = arx.data["From"].apply(utils.extract_email)
    arx.data["domain"] = arx.data["From"].apply(utils.extract_domain)
    arx.data["sender_cat"] = arx.data.apply(normalize_senders_by_domain, axis=1)

    # TODO test for garbage here?


def aggregate_activity(arx, top_n):
    """
    Transform an 'augmented' email archive into a 'wide' format datafame
    that has the activity of each actor (organizational level, where possible)
    for each year.

    TODO: generalize this, with more flexible frequency.
    TODO: Internalize the 'augment' preprocessing.
    """
    grouped = (
        arx.data.groupby(["sender_cat", pd.Grouper(key="Date", freq="Y")])
        .count()
        .reset_index()
        .sort_values("Date")
    )

    ddd = grouped.pivot(columns="sender_cat", index="Date", values="From").fillna(0)

    top_ddd = ddd[ddd.sum().sort_values(ascending=False)[:top_n].index]

    return top_ddd


def influence_from_arx(arx, top_n):
    """
    Return a dataframe with the annual influence of each organizational
    actor, for the top TOP_N most active stakeholders.
    """
    top_n = 50
    augment(arx)
    aaarx = aggregate_activity(arx, top_n)

    return aaarx
