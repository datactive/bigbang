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
        #import pdb; pdb.set_trace()
        #return re_cache['msg_from'].findall(m_from)[0]
        return m_from[m_from.index("(") + 1:m_from.rindex(")")]
    except IndexError:
        print("No change of 'from'")
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
    except ValueError:
        print "Date parsing error on: " 
        print ds
        
        return None
