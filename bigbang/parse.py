from pprint import pprint as pp
import email
import re

def open_mail_archive(filename):
    f = open(filename)

    top_exp = re.compile("From .*\d\d\d\d\n")

    mails = top_exp.split(f.read())

    messages = [email.message_from_string(m) for m in mails if m is not '']

    return messages
