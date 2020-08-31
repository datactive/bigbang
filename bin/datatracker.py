from config.config import CONFIG
from ietfdata.datatracker import *
import os
import pandas as pd

## working group acronym -- should be a command line argument
wg = "httpbisa"

## set up directory for storing metadata files

if not os.path.exists(CONFIG.datatracker_path):
    os.makedirs(CONFIG.datatracker_path)

wg_path = os.path.join(CONFIG.datatracker_path,
                       wg)

if not os.path.exists(wg_path):
    os.makedirs(wg_path)

## initialize datatracker

dt = DataTracker()

group = dt.group_from_acronym(wg)

## metadata extraction function

def extract_data(doc):
    data = {}
    data['title'] = doc.title
    data['time'] = doc.time
    
    data['person'] = [
        dt.person(doc_author.person)
        for doc_author
        in dt.document_authors(doc)
    ]

    data['affiliation'] = [
        doc_author.affiliation
        for doc_author
        in dt.document_authors(doc)
    ]
    data['group-acronym'] = dt.group(doc.group).acronym
    data['type'] = doc.type.uri

    return data

## Begin execution

print("Collecting drafts from datatracker")

# This returns a generator
drafts = dt.documents(group = group,
                      doctype = dt.document_type(
                          DocumentTypeURI("/api/v1/name/doctypename/draft")))

# This loop has been coded so that it's possible to
# renew a crawl for drafts after a network interruption.

# Get the highest valued data storage file
saved_data = [int(x[11:-4]) for x in os.listdir(wg_path)
              if len(x) >= 11 and  x[:11] == "draft_data_"]

max_saved = max(saved_data) if len(saved_data) > 0 else 0

print(f"Starting with draft {max_saved}")

# Begin main loop

print("Creating draft dataframes")

count = 0
collection = []
for draft in drafts:
    if count % 10 == 0:
        print(f"d: {count}")

    if count > max_saved:
        # Only start storing data after the loop is
        # past the number previously saved
        collection.append(extract_data(draft))

        if count > 0 and count % 25 == 0:
            # save batches of 25 records to CSV
            print(f"saving batch {count}")

            fn = os.path.join(wg_path,
                              f"draft_data_{count}.csv")
            draft_df = pd.DataFrame(collection)
            draft_df.to_csv(fn)

            collection = []

    count +=1
