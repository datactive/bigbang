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


def test_split_references():
    refs = " <ye1y9ljtxwk.fsf@orange30.ex.ac.uk>\n\t<055701c16727$b57fed90$8fd6afcf@pixi.com>"
    split = parse.split_references(refs)
    assert len(split) == 2, split


def test_mailman_chain():
    name = "bigbang-dev-test.txt"

    #archive loaded from mbox
    arx = archive.Archive(name,archive_dir="tests/data",mbox=True)

    arx.save("test.csv")

    #archive loaded from stored csv
    arx2 = archive.load("test.csv")

    print arx.data.dtypes
    print arx.data.shape

    assert arx.data.shape == arx2.data.shape, \
        "Original and restored archives are different shapes"

    assert (arx2.data.index == arx.data.index).all(), \
        "Original and restored archives have nonidentical indices"

    assert [t.get_num_messages() for t in arx.get_threads()] == [3,1,2], \
        "Thread message count in mbox archive is off"
    assert [t.get_num_messages() for t in arx2.get_threads()] == [3,1,2], \
        "Thread message count in restored archive is off"

    os.remove("test.csv")
