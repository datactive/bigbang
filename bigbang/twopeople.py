# twopeople.py
#
# Written by Raj Agrawal and Ki Deuk Kim
#
# Contains functions used to analyze communication between two people in mailing list
# Examples can be found in ipython notebook "Collaboration Robustness" in examples folder
# Each function needs a pandas DataFrame called "exchanges" that contains every two-pair
# communication between participants in a mailing list.

from pprint import pprint as pp

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import pytz

import bigbang.graph as graph
import bigbang.mailman as mailman
import bigbang.parse as parse
import bigbang.process as process
from bigbang.archive import Archive


# Gets the target two people A, B to analyze and returns
# the amount of time they communicated in the mailing list
# in TimeDelta type
def duration(exchanges, A, B):
    AtoB = exchanges[exchanges["From_original"] == A]
    AtoB = AtoB[AtoB["From_response"] == B]
    BtoA = exchanges[exchanges["From_original"] == B]
    BtoA = BtoA[BtoA["From_response"] == A]
    if len(AtoB) == 0:
        return max(BtoA["Date"]) - min(BtoA["Date"])
    if len(BtoA) == 0:
        return max(AtoB["Date"]) - min(AtoB["Date"])
    return max(max(AtoB["Date"]), max(BtoA["Date"])) - min(
        min(AtoB["Date"]), min(BtoA["Date"])
    )


# Returns the number of replies that two people A and B sent to
# each other in a tuple (# of replies from A to B, # of replies from B to A)
def num_replies(exchanges, A, B):
    AtoB = exchanges[exchanges["From_original"] == A]
    AtoB = AtoB[AtoB["From_response"] == B]
    BtoA = exchanges[exchanges["From_original"] == B]
    BtoA = BtoA[BtoA["From_response"] == A]
    return (len(AtoB), len(BtoA))


# Returns the reciprocity of communication between two people A and B
# in float type. This expresses how interactively they communicated to each
# other
def reciprocity(exchanges, A, B):
    num = num_replies(exchanges, A, B)
    return float(min(num)) / max(num)


# Finds every unique pair (A, B) from the pandas DataFrame "exchanges"
# and returns them in set data type
def unique_pairs(exchanges):
    pairs = set()
    total_responses = len(exchanges["From_original"])
    for i in range(total_responses):
        pair = (exchanges["From_original"][i], exchanges["From_response"][i])
        pair_reversed = (
            exchanges["From_response"][i],
            exchanges["From_original"][i],
        )
        if pair_reversed not in pairs:
            pairs.add(pair)
    return pairs


# Forms a new Pandas DataFrame that contains information about communication
# between a pair A and B using functions provided above and returns the result
def panda_pair(exchanges, A, B):
    try:
        return pd.DataFrame(
            [
                {
                    "A": A,
                    "B": B,
                    "duration": duration(exchanges, A, B),
                    "num_replies": sum(num_replies(exchanges, A, B)),
                    "reciprocity": reciprocity(exchanges, A, B),
                }
            ]
        )
    except Exception:
        print('No exchange between "%s" and "%s" exists.' % (A, B))


# With given pairs of communication, returns a Pandas DataFrame that contains
# communication information between two people A and B in every pair
def panda_allpairs(exchanges, pairs):
    data_list = []
    for pair in pairs:
        A = pair[0]
        B = pair[1]
        data_list.append(
            {
                "A": A,
                "B": B,
                "duration": duration(exchanges, A, B),
                "num_replies": sum(num_replies(exchanges, A, B)),
                "reciprocity": reciprocity(exchanges, A, B),
            }
        )
    return pd.DataFrame(data_list)
