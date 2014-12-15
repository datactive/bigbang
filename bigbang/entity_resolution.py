import pandas as pd
import numpy as np
import re
namesID = dict();
emailsID = dict();
allID = dict();
nameRegex = re.compile("(\(.*\))")
currID = 1;

def getID(name, email):
    global currID;
    global emailsID
    global namesID
    nameID = False;
    emailID = False;
    if name is not None:
        if name in namesID:
            nameID = namesID[name];
    if email is not None:
        if email in emailsID:
            emailID = emailsID[email]
    
    if (not emailID) and (not nameID):
        store(currID, name, email);
        currID += 1;
        return currID;
    
    if not emailID:
        store(nameID, name, email)
        return nameID
    
    if not nameID:
        store(emailID, name, email)
        return emailID
        
    if emailID != nameID:
        # print("ID MISMATCH! " + email + " " + name)
        store(nameID, name, email)

    return nameID;

def store(id, name, email) :
	if id not in allID:
		allID[id] = {"emails": list(), "names": list()}
	fullID = allID[id];
	namesID[name] = id;
	emailsID[email] = id;
	fullID["names"].append(name);
	fullID["emails"].append(email);



def entityResolve(row, emailCol, nameCol):
    emailAddress = row[emailCol].upper();
    emailAddress = emailAddress.replace(" AT ", "@")
    
    match = nameRegex.search(emailAddress)
    name = None

    if (match is not None):
        name = match.group(0) #unused info for now
        emailAddress = emailAddress.replace(name, "");
        name = name.replace("(", "")
        name = name.replace(")", "")
    if nameCol is not None :
        name = row[nameCol].upper()
    row["Person-ID"] = getID(name, emailAddress)
    return row