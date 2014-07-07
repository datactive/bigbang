from pprint import pprint as pp
import email
import re
import dateutil.parser as dp
import pytz

re_cache = {
  'top_exp'     : re.compile("From .*\d\d\d\d\n"),
  'msg_id'      : re.compile("<\S*@\S*>"),
  'msg_from'    : re.compile("\(([^()]+)\)")
}

def open_mail_archive(filename):
    with open(filename, 'r') as f:
        mails = re_cache['top_exp'].split(f.read())
        return [email.message_from_string(m) for m in mails if m is not '']

def split_references(refs):
    return re_cache['msg_id'].findall(refs)

def get_refs(refs):
    return re_cache['msg_id'].findall(refs)

def clean_mid(mid):
    try:
        return get_refs(mid)[0]
    except IndexError:
        print mid
        return mid

def clean_from(m_from):
    try:
        return re_cache['msg_from'].findall(m_from)[0]
    except IndexError:
        return m_from

def get_date(message):
    ds = message.get('Date')
    try:
        # some mail clients add a parenthetical timezone
        ds = re.sub("\(.*$","",ds)
        ds = re.sub("--","-",ds)
        ds = re.sub(" Hora.*$","",ds)

        date = dp.parse(ds)

        # this adds noise and could raise trouble
        if date.tzinfo is None:
            date = pytz.utc.localize(date)

        return date
    except TypeError:
        print "Date parsing error on: " 
        print ds
        
        return None
