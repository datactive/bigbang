import datetime
import email.utils
import re
from functools import partial

import Levenshtein
import networkx as nx
import numpy as np
import pandas as pd

from bigbang.parse import get_date


def consolidate_senders_activity(activity_df, to_consolidate):
    """
    takes a DataFrame in the format returned by activity
    takes a list of tuples of format ('from 1', 'from 2') to consolidate
    returns the consolidated DataFrame (a copy, not in place)
    """

    df = activity_df.copy(deep=True)
    for consolidate in to_consolidate:
        column_a, column_b = consolidate
        if column_a in df.columns and column_b in df.columns:
            df[column_a] = df[column_a] + df[column_b]
            df.drop(column_b, inplace=True, axis=1)  # delete the second column
    return df


def matricize(series, func):
    """
    create a matrix by applying func to pairwise combos of elements in a Series
    returns a square matrix as a DataFrame
    should return a symmetric matrix if func(a,b) == func(b,a)
    should return the identity matrix if func == '=='
    """
    matrix = pd.DataFrame(columns=series, index=series)
    for index, element in enumerate(series):
        for second_index, second_element in enumerate(series):
            matrix.iloc[index, second_index] = func(element, second_element)

    return matrix


def minimum_but_not_self(column, dataframe):
    minimum = 100
    for index, value in dataframe[column].items():
        if index == column:
            continue
        if value < minimum:
            minimum = value
    return minimum


def sorted_matrix(from_dataframe, limit=None, sort_key=None):
    """
        Takes a dataframe with 'from' fields for column headers
    .
        Returns a sorted distance matrix for the column headers,
        using from_header_distance (see method).
    """
    if limit is None:
        limit = len(from_dataframe.columns)

    distancedf = matricize(
        from_dataframe.columns[: limit - 1], from_header_distance
    )

    # specify that the values in the matrix are integers
    df = distancedf.astype(int)

    # unless otherwise specified, sort to minimize the integer values with rows other than yourself
    sort_key = (
        sort_key
        if sort_key is not None
        else partial(minimum_but_not_self, dataframe=df)
    )

    new_columns = sorted(df.columns[: limit - 1], key=sort_key)
    new_df = df.reindex(index=new_columns, columns=new_columns)

    return new_df


def resolve_sender_entities(act, lexical_distance=0):
    """
    Given an Archive's activity matrix, return a dict of lists, each containing
    message senders ('From' fields) that have been groups to be
    probably the same entity.
    """

    # senders orders by descending total activity
    senders = act.sum(0).sort_values(ascending=False)

    return resolve_entities(
        senders, from_header_distance, threshold=lexical_distance
    )


def resolve_entities(significance, distance_function, threshold=0):
    """
    Takes a Series mapping entities (index) to significance (values, numerical).

    Resolves the entities based on a lexical distance function.

    Returns a dictionary of labeled (keys) entity lists (values).
    Key is the most significant member of the entity list.
    """
    entities = significance.index

    # entities in lexical order
    entities_lex = entities.sort_values()
    entities_lex_dict = dict([(p[1], p[0]) for p in enumerate(entities_lex)])

    n = len(entities)
    # binary matrix of similarity between entries
    sim = np.zeros((n, n))

    # find similarity
    for i in range(n):
        name = entities[i]
        i = entities_lex_dict[name]

        # checking only lexically close entries and
        # in proportion to total activity
        # is a performance hack.
        for j in range(i - (n - i + 1) // 2, i + (n - i + 1) // 2):
            d = distance_function(entities_lex[i], entities_lex[j])
            sim[i, j] = d <= threshold

    # An entity is a connected component of the resulting graph
    G = nx.Graph(sim)
    entities_list = [
        [entities_lex[j] for j in x] for x in nx.connected_components(G)
    ]

    # given each entity a label based on its most active 'member'
    entities_dict = {}
    for e in entities_list:
        # TODO: tighten up this labeling function
        label = sorted(e, key=lambda n: significance[n], reverse=True)[0]
        entities_dict[label] = e

    return entities_dict


ren = r"([\w\+\.\-]+(\@| at )[\w+\.\-]*) \((.*)\)"


def from_header_distance(a, b, verbose=False):
    """
    A distance measure specifically for the 'From' header of emails.
    Normalizes based on common differences in client handling of email,
    then computes Levenshtein distance between components of the field.
    """
    # this translate table is one way you are supposed to
    # delete characters from a unicode string
    stop_characters = str('"<>')
    stop_characters_map = dict((ord(char), None) for char in stop_characters)

    a_normal = ""
    b_normal = ""

    try:
        a_normal = (
            str(a).lower().translate(stop_characters_map).replace(" at ", "@")
        )
    except UnicodeDecodeError:
        a_normal = (
            a.decode("utf-8")
            .lower()
            .translate(stop_characters_map)
            .replace(" at ", "@")
        )

    try:
        b_normal = (
            str(b).lower().translate(stop_characters_map).replace(" at ", "@")
        )
    except UnicodeDecodeError:
        b_normal = (
            b.decode("utf-8")
            .lower()
            .translate(stop_characters_map)
            .replace(" at ", "@")
        )

    ag = re.match(ren, a_normal)
    bg = re.match(ren, b_normal)

    dist = float("inf")

    if ag is None or bg is None:
        if verbose:
            print("malformed pair:")
            print(a)
            print(b)
        dist = Levenshtein.distance(a_normal, b_normal)
    else:
        dist = Levenshtein.distance(
            ag.groups()[0], bg.groups()[0]
        ) + Levenshtein.distance(ag.groups()[1], bg.groups()[1])

        if len(ag.groups()[2]) > 5 and len(ag.groups()[2]) > 5:
            dist = min(
                dist, Levenshtein.distance(ag.groups()[2], bg.groups()[2])
            )

    return dist


def eij(m, parts, i, j):
    total_edges = m.sum().sum()

    part_i = parts[i]
    part_j = parts[j]

    edges_in_range = m[np.ix_(np.array(part_i), np.array(part_j))]

    return edges_in_range.sum().sum() / total_edges


def ai(m, parts, i):
    total = 0

    for j in range(len(parts)):
        total = total + eij(m, parts, i, j)

    return total


def bi(m, parts, i):
    total = 0

    for j in range(len(parts)):
        total = total + eij(m, parts, j, i)  # note switched i,j

    return total


def modularity(m, parts):
    """
    Compute modularity of an adjacency matrix.
    Use metric from:
        Zanetti, M. and Schweitzer, F. 2012.
        "A Network Perspective on Software Modularity"
        ARCS Workshops 2012, pp. 175-186.
    """

    expected = 0
    actual = 0

    for i in range(len(parts)):
        expected = expected + ai(m, parts, i) * bi(m, parts, i)
        actual = actual + eij(m, parts, i, i)

    q = (actual - expected) / (1 - expected)

    return q


def domain_name_from_email(name):
    address = email.utils.parseaddr(name)[1]
    if "@" in address:
        domain = address.split("@")[1]
    else:
        domain = address.split(" at ")[1]
    return domain.lower()


def containment_distance(a, b):
    """
    A case-insensitive distance measure on strings.

    Returns:
     - 0 if strings are identical
     - positive infinity if neither string contains
       the other
     - 1 / (minimum string length) if one string contains the other.

    Good for Organizations.
    I.e. "cisco" "Cisco" "Cisco Systems" are all 'close' (< .2)
    """
    a = a.lower()
    b = b.lower()

    base = 0

    if a == b:
        base = 0
    if a in b or b in a:
        base = 1
    else:
        base = float("inf")

    modifier = min(len(a), len(b))

    if modifier == 0:
        return float("inf")
    else:
        return base / modifier
