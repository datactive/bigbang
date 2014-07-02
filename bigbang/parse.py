from pprint import pprint as pp
import email
import re
import dateutil.parser as dparse


re_cache = {
  'top_exp'     : re.compile("From .*\d\d\d\d\n"),
  'msg_id'      : re.compile("<\S*@\S*>"),
  'msg_from'    : re.compile("\(([^()]+)\)")
}

def open_mail_archive(filename):
    f = open(filename)

    mails = re_cache['top_exp'].split(f.read())

    messages = [email.message_from_string(m) for m in mails if m is not '']

    return messages

def split_references(refs):
    return msg_id_re.findall(refs)

def get_refs(refs):
    return msg_id_re.findall(refs)

def clean_mid(mid):
    return get_refs(mid)[0]

def clean_from(m_from):
    return re_cache['msg_from'].findall(m_from)[0]
