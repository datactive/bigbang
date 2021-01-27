import os
from pathlib import Path

import numpy.testing as npt
import pytest

from bigbang import listserv

dir_test_base = Path(__file__).parent.absolute()
dir_path_data = str(dir_test_base / "data/3GPP/") + "/"
file_id = "3GPP_TSG_SA_WG2_UPCON.LOG*"


@pytest.fixture(name="file_paths", scope="module")
def test__get_all_file():
    file_paths = listserv._get_all_file(dir_path_data, file_id)
    assert len(file_paths) == 2
    return file_paths


@pytest.fixture(name="temp_file_path", scope="module")
def test__create_temporary_file():
    temp_file_path = listserv._create_temporary_file()
    assert os.path.isfile(temp_file_path)
    return temp_file_path


@pytest.fixture(name="content", scope="module")
def read_listserv_file_content(file_paths):
    file_path = file_paths[0]  # select one file path from list
    file = open(file_path, "r")
    content = file.readlines()
    return content


@pytest.fixture(name="line_nrs_header_start", scope="module")
def test__get_line_numbers_of_header_starts(content):
    lnrs_header_start_received = listserv._get_line_numbers_of_header_starts(
        content
    )
    lnrs_header_start_expected = [0, 265, 496, -1]
    assert all(
        [
            a == b
            for a, b in zip(
                lnrs_header_start_received, lnrs_header_start_expected
            )
        ]
    )
    return lnrs_header_start_received


@pytest.fixture(name="line_nrs_header_end", scope="module")
def test__get_line_numbers_of_header_ends(content, line_nrs_header_start):
    lnrs_header_end_received = listserv._get_line_numbers_of_header_ends(
        content, line_nrs_header_start
    )
    lnrs_header_end_expected = [30, 297, 506]
    assert all(
        [
            a == b
            for a, b in zip(lnrs_header_end_received, lnrs_header_end_expected)
        ]
    )
    return lnrs_header_end_received


def test__get_header(file_paths, line_nrs_header_start, line_nrs_header_end):
    file_path = file_paths[0]  # select one file path from list
    file = open(file_path, "r")
    content = file.readlines()
    header_dic = listserv._get_header(
        content[line_nrs_header_start[0] : line_nrs_header_end[0] + 1]
    )
    header_keys_received = list(header_dic.keys())
    header_keys_expected = [
        "Date",
        "Reply-To",
        "From",
        "Subject",
        "Comments",
        "Content-Type",
        "MIME-Version",
        "Message-ID",
        "Mm-Date",
        "Mm-From",
        "Mm-Name",
        "In-Reply-To",
    ]
    assert all(
        [a == b for a, b in zip(header_keys_received, header_keys_expected)]
    )


def test__convert_to_mailman(file_paths, temp_file_path):
    file_path = file_paths[0]  # select one file path from list
    listserv._convert_to_mailman(file_path, temp_file_path)
    file = open(temp_file_path, "r")
    content = file.readlines()
    print(content[3])
    assert (
        content[2]
        == "From b'Andreas.Maeder@NECLAB.EU' Thu Aug  1 10:46:56 2013\n"
    )
    assert content[4] == "MIME-Version: 1.0 \n"


def test__from_file(file_paths):
    file_path = file_paths[0]  # select one file path from list
    df = listserv.from_file(file_path)
    assert len(df.index.values) == 3
    columns_received = list(df.columns.values)
    columns_expected = [
        "From",
        "Subject",
        "Date",
        "In-Reply-To",
        "References",
        "Body",
    ]
    assert all([a == b for a, b in zip(columns_received, columns_expected)])


def test__from_files():
    df = listserv.from_files([dir_path_data], [file_id])
    print(len(df.index.values))
    assert len(df.index.values) == 9
    columns_received = list(df.columns.values)
    columns_expected = [
        "From",
        "Subject",
        "Date",
        "In-Reply-To",
        "References",
        "Body",
    ]
    assert all([a == b for a, b in zip(columns_received, columns_expected)])
