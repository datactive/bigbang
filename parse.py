from pprint import pprint as pp
import re

## TODO: deal with the occasional RE: block that gets treated like a header, as in 
## Message-ID: <Pine.SOL.4.30.0111011916360.17706-100000@mimosa.csv.warwick.ac.uk>

def open_mail_archive(filename):
    f = open(filename)

    top_exp = re.compile("From .*\d\d\d\d\n")

    mails = top_exp.split(f.read())

    mails = [m for m in mails if m is not '']

    return mails

# mexp = re.compile("From: (.*)\nDate: (.*)\nSubject: ([-\w\s[\]():]*)\n(?:In-Reply-To: ([-\w\d\s[\]()<>]*))?\n?(?:References: ([-\w\d\s[\]()<>]*))?\n?Message-ID: (.*)(\n\n((?:.*\n)*.*)")

header_exp = re.compile("From: (.*)\nDate: (.*)\nSubject: (.*)(?:In-Reply-To: (.*)\n)?(?:References: (.*)\n)?",re.DOTALL)

def mail_to_dict(mail):

    rep = {}

    #split out the headers and get 
    parts = re.split("Message-ID: (<.*>)\n\n",mail)

    rep["Message-ID"] = parts[1]
    rep["Message"] = parts[2]

    headers = re.split("([\w-]*): ",parts[0])

    #pop preceding empty entry
    headers.pop(0)

    while len(headers) > 0:
        key = headers.pop(0)
        value = headers.pop(0).rstrip()
        rep[key] = value
    
    return rep

mails = open_mail_archive("archives/numpy-discussion/2001-November.txt")
dicts = [mail_to_dict(m) for m in mails]
rejects = [m for m in mails if mail_to_dict(m) is None]

#pp(dicts)
