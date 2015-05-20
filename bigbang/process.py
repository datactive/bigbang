from bigbang.parse import get_date
import pandas as pd
import datetime
import numpy as np
import email.utils
import re

import Levenshtein
from functools import partial

# takes a DataFrame in the format returned by activity
# takes a list of tuples of format ('from 1', 'from 2') to consolidate
# returns the consolidated DataFrame (a copy, not in place)


def consolidate_senders_activity(activity_df, to_consolidate):
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
    for index, value in dataframe[column].iteritems():
        if index == column:
            continue
        if value < minimum:
            minimum = value
    return minimum


def sorted_matrix(from_dataframe,limit=None,sort_key=None):
    if limit is None:
        limit = len(from_dataframe.columns)

    distancedf = matricize(from_dataframe.columns[:limit], from_header_distance)

    # specify that the values in the matrix are integers
    df = distancedf.astype(int)

    if sort_key is not None:
        #sort_for_this_df = partial(minimum_but_not_self, dataframe=df)
        new_columns = sorted(df.columns, key=sort_key)

    #new_df = df.reindex(index=new_columns, columns=new_columns)

    return df #new_df



ren = "([\w\+\.\-]+(\@| at )[\w+\.\-]*) \((.*)\)"
def from_header_distance(a, b):
    """
    A distance measure specifically for the 'From' header of emails.
    Normalizes based on common differences in client handling of email,
    then computes Levenshtein distance.
    """
    # this translate table is one way you are supposed to
    # delete characters from a unicode string
    stop_characters = unicode('"<>')
    stop_characters_map = dict((ord(char), None) for char in stop_characters)

    a_normal = unicode(a).lower().translate(stop_characters_map).replace(' at ','@')
    b_normal = unicode(b).lower().translate(stop_characters_map).replace(' at ','@')

    ag = re.match(ren,a_normal)
    bg = re.match(ren,b_normal)
    
    dist = float("inf")

    if ag is None or bg is None:
        print "malformed pair:"
        print ag
        print bg
        dist = Levenshtein.distance(a_normal, b_normal)
    else:
        dist = Levenshtein.distance(ag.groups()[0],bg.groups()[0]) \
               + Levenshtein.distance(ag.groups()[1],bg.groups()[1])

        if len(ag.groups()[2]) > 5 and len(ag.groups()[2]) > 5:
            dist = min(dist,Levenshtein.distance(ag.groups()[2],bg.groups()[2]))

    return dist
