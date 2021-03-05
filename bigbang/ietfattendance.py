import logging

import bs4
import pandas as pd
import requests

# meeting number, which tables contain information.
formats = {
    91: [2],
    92: [2],
    93: [1],
    94: [1],
    95: [1],
    96: [1],
    97: [1],
    98: [1],
    99: [1],
    100: [1],
    101: [1],
    102: [1],
    103: [1],
    104: [1, 2, 3],
    105: [1, 2, 3],
    106: [1, 2, 3],
    107: [1, 2, 3],
}

meeting_number_range = range(91, 107)

### TODO: Mapping from meeting number to dates

### TODO: Add to BigBang

### TODO: Automated test?


def attendance_url(mn):
    return "https://www.ietf.org/registration/ietf%d/attendance.py" % (mn)


def parse_tr(raw_tr):
    tds = pd.Series(raw_tr.find_all("td"))
    texts = tds.apply(lambda x: x.text)
    return texts


def table_to_df(table):
    headers = [
        th.text
        for th in table.find_all("th")
        if th.has_attr("class") and th.attrs["class"][0] == "reg"
    ]
    columns = {i: h for i, h in enumerate(headers)}
    return (
        pd.Series(table.find_all("tr")).apply(parse_tr).rename(columns=columns)
    )


def attendance_tables(mn):
    url = attendance_url(mn)
    r = requests.get(url)
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    tables = soup.find_all("table")

    dfs = [table_to_df(table) for table in tables]
    data = [dfs[i] for i in formats[mn]]

    ### This is a hack
    if len(data) > 1:
        data[0]["On-Site"] = "Yes"
        data[1]["On-Site"] = "NYA"
        data[2]["On-Site"] = "Remote"

        data = pd.concat(data, axis=0)
    else:
        data = data[0]

    logging.debug(data.shape)

    return data


def all_attendance():
    all_attendance_tables = []

    for mn in meeting_number_range:
        logging.info("Collecting attendance data for meeting %s" % (mn))
        data = attendance_tables(mn)
        data["mn"] = mn
        all_attendance_tables.append(data)

    alld = pd.concat(all_attendance_tables, sort=True)

    return alld
