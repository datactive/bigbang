from pprint import pprint as pp
import email
import re
import dateutil.parser as dp
import pytz
import warnings

re_cache = {
    'top_exp': re.compile("From .*\d\d\d\d\n"),
    'msg_id': re.compile("<\S*@\S*>")
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
    """
    Return a person's name extracted from 'From' field
    of email, based on heuristics.
    """

    cleaned = m_from

    try:
        if "(" in m_from:
            cleaned = m_from[m_from.index("(") + 1:m_from.rindex(")")]
        elif "<" in m_from:
            # if m_from.index("<") > -1:
            cleaned = m_from[0:m_from.index("<") - 1]

    except ValueError:
        warnings.warn("%s is hard to clean" % (m_from))

    cleaned = cleaned.strip("\"")

    return cleaned

def guess_first_name(cleaned_from):
    """
    Attempt to extract a person's first name from the cleaned version of their name
    (from a 'From' field). This may or may not be the given name. Returns None
    if heuristic doesn't recognize a separable first name.
    """
    
    cleaned_from = cleaned_from.strip() # remove leading and trailing whitespace
    
    # accomodate Last, First name format
    if ',' in cleaned_from:
        parts = cleaned_from.split(',')
        if len(parts) > 2:
            return None
        first_part = parts[1].strip()
        
        if ' ' in first_part:   # First Middle Last? Or something entirely different
            return None
        else:
            return first_part
        
    elif ' ' in cleaned_from:
        parts = cleaned_from.split(' ')
        if len(parts) == 2: # e.g. First Last
            return parts[0]
        return None
    else:   # no spaces or commas? with a single name, more likely to be a handle than a given name
        return None

def get_date(message):
    ds = message.get('Date')
    try:
        # some mail clients add a parenthetical timezone
        ds = re.sub("\(.*$", "", ds)
        ds = re.sub("--", "-", ds)
        ds = re.sub(" Hora.*$", "", ds)

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
