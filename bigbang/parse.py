from pprint import pprint as pp
import email
import re
import dateutil.parser as dparse

def open_mail_archive(filename):
    f = open(filename)

    top_exp = re.compile("From .*\d\d\d\d\n")

    mails = top_exp.split(f.read())

    messages = [email.message_from_string(m) for m in mails if m is not '']

    return messages

msg_id_re = re.compile("<\S*@\S*>")

def split_references(refs):
    return msg_id_re.findall(refs)

msg_id_re = re.compile("<\S*@\S*>")

def get_refs(refs):
    return msg_id_re.findall(refs)

def clean_mid(mid):
    return get_refs(mid)[0]

msg_from_re = re.compile("\(([^()]+)\)")

def clean_from(m_from):
    return msg_from_re.findall(m_from)[0]
