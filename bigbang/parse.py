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
