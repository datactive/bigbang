from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from dateutil.parser          import *
import json as json
import pandas as pd
import re

dt = DataTrackerExt()


def draft_authors_from_working_group(acr):
    """
    Get a dataframe of all authors of drafts published
    by the working group.
    """

    # identify group
    g  = dt.group_from_acronym(acr)

    records = []
    # get drafts.
    # filter by rfc status here?
    for draft in dt.documents(group=g, doctype=dt.document_type_from_slug("draft")): # status argument
        # interested in all submissions, or just the most recent?
        #
        submissions =  [dt.submission(sub_url) for sub_url in draft.submissions]
        submissions = sorted(submissions, key = lambda s : s.submission_date, reverse=True)

        if len(submissions) > 0 :
            latest = submissions[0]

            authors_text = latest.authors
        
            try:
                at = authors_text.replace("'", "\"")
                at = at.replace("None", "null")
                authors = json.loads(at)
            except Exception as e:
                authors = [{'raw_text' : authors_text}]

            for a in authors:
                a['submission_date'] = latest.submission_date
                a['draft_uri'] = latest.draft.uri
                a['title'] = latest.title

            records.append(authors)

    records = sum(records, [])

    df = pd.DataFrame.from_records(records)

    return df