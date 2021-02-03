import re

import numpy as np
import pandas as pd

namesID = dict()
emailsID = dict()
allID = dict()
nameRegex = re.compile(r"(\(.*\))")
currID = 1


def getID(name, email):
    """Get ID from a name and email."""

    global currID
    global emailsID
    global namesID
    nameID = False
    emailID = False
    if name is not None:
        if name in namesID:
            nameID = namesID[name]
    if email is not None:
        if email in emailsID:
            emailID = emailsID[email]

    if (not emailID) and (not nameID):
        store(currID, name, email)
        currID += 1
        return currID

    if not emailID:
        store(nameID, name, email)
        return nameID

    if not nameID:
        store(emailID, name, email)
        return emailID

    if emailID != nameID:
        # print("ID MISMATCH! " + email + " " + name)
        store(nameID, name, email)
    else:
        if emailID not in allID:
            store(emailID, name, email)

    return nameID


def store(id, name, email):
    """Store name and email by ID."""

    if id not in allID:
        allID[id] = {"emails": list(), "names": list()}
    fullID = allID[id]
    namesID[name] = id
    emailsID[email] = id
    fullID["names"].append(name)
    fullID["emails"].append(email)


def name_for_id(id):
    """Return name by ID."""

    if id in allID:
        if "names" in allID[id] and len(allID[id]["names"]) > 0:
            return allID[id]["names"][0]
    return "UNKNOWN " + str(id)


def entity_resolve(row, emailCol, nameCol):
    """Return a row with name and email by ID."""

    emailAddress = row[emailCol].upper()
    emailAddress = emailAddress.replace(" AT ", "@")

    match = nameRegex.search(emailAddress)
    name = None

    if match is not None:
        name = match.group(0)  # unused info for now
        emailAddress = emailAddress.replace(name, "")
        name = name.replace("(", "")
        name = name.replace(")", "")
    if nameCol is not None:
        name = row[nameCol].upper()
    row["Person-ID"] = getID(name, emailAddress)
    return row
