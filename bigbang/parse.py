from pprint import pprint as pp
import email
import re

## TODO: deal with the occasional RE: block that gets treated like a header, as in 
## Message-ID: <Pine.SOL.4.30.0111011916360.17706-100000@mimosa.csv.warwick.ac.uk>

def open_mail_archive(filename):
    f = open(filename)

    top_exp = re.compile("From .*\d\d\d\d\n")

    mails = top_exp.split(f.read())

    messages = [email.message_from_string(m) for m in mails if m is not '']

    return messages
