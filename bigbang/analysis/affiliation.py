from bigbang.analysis.influence import *
from bigbang.analysis.utils import localize_to_utc
from bigbang.archive import Archive

affil_start_date_col_name = "Time start (mm/yyyy)"
affil_end_date_col_name = "Time end (mm/yyyy)"
affil_affiliation_col_name = "Affiliation"


def affiliated_influence(arx, affiliations, corrections={}, top_n=50):
    ## this is defined in influence.py, and builds a sender_cat column
    ## based on email domain
    augment(arx)

    # first pass at corrections: normalize the names of senders
    adata = arx.data.copy()
    adata["sender_cat"] = adata["sender_cat"].map(lambda x: corrections.get(x, x))
    arx = Archive(adata)

    ## this further looks up the email author in the affiliations table
    ## and modifies the sender_cat column
    arx.data["sender_cat"] = arx.data.apply(
        lambda mrow: lookup_affiliation(mrow["sender_cat"], mrow["Date"], affiliations),
        axis=1,
    )

    # second pass at corrections: normalize the names of companies.
    adata = arx.data.copy()
    adata["sender_cat"] = adata["sender_cat"].map(lambda x: corrections.get(x, x))
    arx = Archive(adata)

    top_ddd = aggregate_activity(Archive(adata), top_n)

    return top_ddd


def lookup_affiliation(name, date, affiliation_data):
    """
    Find the affiliation of a name on a particular date,
    given an affiliation data file.
    """
    name_affils = affiliation_data[
        affiliation_data["Name"].apply(lambda x: str(x).strip()) == name
    ]

    date = localize_to_utc(date)

    for na_row in name_affils.iterrows():
        if (
            date > na_row[1][affil_start_date_col_name]
            and date < na_row[1][affil_end_date_col_name]
        ):
            return na_row[1][affil_affiliation_col_name]

    name = name.strip() if isinstance(name, str) else name

    return name
