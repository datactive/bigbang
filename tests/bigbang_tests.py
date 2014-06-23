from nose.tools import *
import bigbang.parse as parse
import os

test_txt = ""

def setup():
    pass
    
def teardown():
    pass

@with_setup(setup, teardown)
def test_parse():

    dirname = os.path.dirname(os.path.abspath(__file__))
    test_file_name = os.path.join(dirname,"2001-November.txt")

    mails = parse.open_mail_archive(test_file_name)

    messages = [parse.mail_to_dict(m) for m in mails]

    for message in messages:
        assert len(message.items()) <= 6, "too many fields:\n%s" % (message)
