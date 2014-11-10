from nose.tools import *
import bigbang.archive as archive
import bigbang.mailman as mailman
import bigbang.parse as parse
import mailbox
import os

test_txt = ""


def setup():
    pass


def teardown():
    pass


@with_setup(setup, teardown)
def test_parse():

    dirname = os.path.dirname(os.path.abspath(__file__))
    test_file_name = os.path.join(dirname, "2001-November.txt")

    messages = mailbox.mbox(test_file_name, create=False).values()

    for message in messages:
        assert len(message.items()) <= 6, "too many fields:\n%s" % (message)


def test_split_references():
    refs = " <ye1y9ljtxwk.fsf@orange30.ex.ac.uk>\n\t<055701c16727$b57fed90$8fd6afcf@pixi.com>"
    split = parse.split_references(refs)
    assert len(split) == 2, split


def test_mailman_chain():
    url = "http://mail.scipy.org/pipermail/ipython-dev/"

    arx = archive.Archive(url)

    arx.save("test.csv")

    arx2 = archive.load("test.csv")

    arx3 = archive.Archive("ipython-dev")

    assert arx.data.shape == arx.data.shape

    os.remove("test.csv")
