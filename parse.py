from pprint import pprint as pp
import re

f = open("archives/numpy-discussion/2001-November.txt")

top_exp = re.compile("From .*\d\d\d\d\n")

mails = top_exp.split(f.read())

mails = [m for m in mails if m is not '']

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

dicts = [mail_to_dict(m) for m in mails]
rejects = [m for m in mails if mail_to_dict(m) is None]

pp(dicts)
