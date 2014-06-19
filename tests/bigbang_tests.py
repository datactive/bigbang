from nose.tools import *
import bigbang
import os

test_txt = ""

def setup():
    # load a sample txt file
    dirname = os.path.dirname(os.path.abspath(__file__))

    test_file = open(os.path.join(dirname,"2001-November.txt"))

    global test_txt
    test_txt = test_file.read()

def teardown():
    print "TEAR DOWN!"

@with_setup(setup, teardown)
def test_basic():

    print test_txt
    if len(test_txt) > 0:
        pass
    else:
        assert False
    print "I RAN!"
