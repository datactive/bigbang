from nose.tools import *
from testfixtures import LogCapture
from bigbang import repo_loader
import bigbang.archive as archive
import bigbang.mailman as mailman
import bigbang.parse as parse
import bigbang.process as process
import bigbang.utils as utils
import mailbox
import os
import networkx as nx
import pandas as pd

from config.config import CONFIG

test_txt = ""

def test_git_dependancy():
    repo = repo_loader.get_repo("https://github.com/sbenthall/bigbang.git", in_type = "remote")

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

    # smoke test entity resolution
    arx2.resolve_entities()

    os.remove("test.csv")

def test_clean_message():
    name = "2001-November.txt"

    arx = archive.Archive(name,archive_dir="tests/data",mbox=True)

    body = arx.data['Body'][ '<E165uMn-0002IJ-00@spock.physics.mcgill.ca>']

    assert "But seemingly it is even stranger than this." in body, \
        "Selected wrong message"

    assert "Is it a problem of lapack3.0 of of" in body, \
        "Quoted text is not in uncleaned message"

    assert "Is it a problem of lapack3.0 of of" not in utils.clean_message(body), \
        "Quoted text is in cleaned message"

    
def test_from_header_distance():
    a = 'Fernando.Perez at colorado.edu (Fernando.Perez at colorado.edu)'
    b = 'Fernando.Perez at colorado.edu (Fernando.Perez@colorado.edu)'

    assert process.from_header_distance(a,b) == 0, \
        "from_header_distance computing incorrect value"

    a = ''
    b = ''

    assert True, \
        "from_header_distance computing incorrect value"

def test_email_entity_resolution():
    name = "2001-November.txt"

    arx = archive.Archive(name,archive_dir="tests/data",mbox=True)

    e = process.resolve_sender_entities(arx.get_activity(resolved=False))

    eact = utils.repartition_dataframe(arx.get_activity(),e)

    assert True, "email entity resolution crashed"

def test_labeled_blockmodel():
    g = nx.DiGraph()

    g.add_edge(0,1)
    g.add_edge(0,2)
    g.add_edge(0,3)
    g.add_edge(0,4)

    p = {'B': [1,2,3,4], 'A': [0]}

    bg = utils.labeled_blockmodel(g,p)

    assert list(bg.edges(data=True))[0][2]['weight'] == 4.0, \
        "Incorrect edge weight in labeled blockmodel"

    assert list(bg.edges()) == [('A','B')], \
        "Incorrected edges in labeled blockmodel"

def test_valid_urls():
    test_urls_path = os.path.join(CONFIG.test_data_path, 'urls-test-file.txt')
    with LogCapture() as l:
        urls = mailman.urls_to_collect(test_urls_path)
        assert "#ignored" not in urls, "failed to ignore a comment line"
        assert "http://www.example.com/1" in urls, "failed to find valid url"

        assert "http://www.example.com/2/" in urls, "failed to find valid url, whitespace strip issue"
        assert "https://www.example.com/3/" in urls, "failed to find valid url, whitespace strip issue"
        assert "invalid.com" not in urls, "accepted invalid url"
        assert len(l.actual()) == 2, "wrong number of log entries"
        for (fromwhere, level, msg) in l.actual():
            assert level == "WARNING", "logged something that wasn't a warning"
        assert len(urls) == 3, "wrong number of urls parsed from file"

def test_empty_list_compute_activity_issue_246():
    test_df_csv_path = os.path.join(CONFIG.test_data_path, 'empty-archive-df.csv')
    df = pd.read_csv(test_df_csv_path)

    with assert_raises(mailman.MissingDataException):
        empty_archive = archive.Archive(df)
        activity = empty_archive.get_activity()

def test_mailman_normalizer():
    browse_url = 'https://mailarchive.ietf.org/arch/browse/ietf/'
    search_url = 'https://mailarchive.ietf.org/arch/search/?email_list=ietf'
    random_url = 'http://example.com'

    better_url = 'https://www.ietf.org/mail-archive/text/ietf/'

    assert mailman.normalize_archives_url(browse_url) == better_url, "failed to normalize"
    assert mailman.normalize_archives_url(search_url) == better_url, "failed to normalize"
    assert mailman.normalize_archives_url(random_url) == random_url, "should not have changed other url"

def test_mailman_list_name():
    ietf_archive_url = 'https://www.ietf.org/mail-archive/text/ietf/'
    w3c_archive_url = 'https://lists.w3.org/Archives/Public/public-privacy/'
    random_url = 'http://example.com'

    assert mailman.get_list_name(ietf_archive_url) == 'ietf', "failed to grab ietf list name"
    assert mailman.get_list_name(w3c_archive_url) == 'public-privacy', "failed to grab w3c list name"
    assert mailman.get_list_name(random_url) == random_url, "should not have changed other url"

def test_activity_summary():
    list_url = 'https://lists.w3.org/Archives/Public/test-activity-summary/'
    activity_frame = mailman.open_activity_summary(list_url, archive_dir=CONFIG.test_data_path)

    assert str(type(activity_frame)) == "<class 'pandas.core.frame.DataFrame'>", "not a DataFrame?"
    assert len(activity_frame.columns) == 1, "activity summary should have one column"