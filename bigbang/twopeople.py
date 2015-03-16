from bigbang.archive import Archive
import bigbang.parse as parse
import bigbang.graph as graph
import bigbang.mailman as mailman
import bigbang.process as process
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from pprint import pprint as pp
import pytz

def duration(exchanges, A, B):
    AtoB = exchanges[exchanges['From_original'] == A]
    AtoB = AtoB[AtoB['From_response'] == B]
    BtoA = exchanges[exchanges['From_original'] == B]
    BtoA = BtoA[BtoA['From_response']==A]
    return max(max(AtoB['Date']), max(BtoA['Date'])) - min(min(AtoB['Date']), min(BtoA['Date']))
    
def num_replies(exchanges, A, B):
    AtoB = exchanges[exchanges['From_original'] == A]
    AtoB = AtoB[AtoB['From_response'] == B]
    BtoA = exchanges[exchanges['From_original'] == B]
    BtoA = BtoA[BtoA['From_response'] == A]
    return (len(AtoB), len(BtoA))
    
def reciprocity(exchanges, A, B):
    num = num_replies(exchanges, A, B)
    return float(min(num)) / max(num)

def unique_pairs(exchanges):
    pairs = set()
    total_responses = len(exchanges['From_original'])
    for i in range(total_responses):
        pair = (exchanges['From_original'][i], exchanges['From_response'][i]) 
        pair_reversed = (exchanges['From_response'][i], exchanges['From_original'][i])
        if pair_reversed not in pairs:
            pairs.add(pair)
    return pairs

def panda_pair(exchanges, A, B):
    try:
        return pd.DataFrame([{'A': A, 'B': B, 'duration':duration(exchanges, A, B), 'num_replies': sum(num_replies(exchanges, A, B)), 'reciprocity':reciprocity(exchanges, A, B)}])
    except:
        print 'No exchange between "%s" and "%s" exists.' % (A, B)

def panda_allpairs(exchanges, pairs):
    data_list = []
    for pair in pairs:
        A = pair[0]
        B = pair[1] 
        try:
            data_list.append({'A': A, 'B': B, 'duration':duration(exchanges, A, B), 'num_replies': sum(num_replies(exchanges, A, B)), 'reciprocity':reciprocity(exchanges, A, B)})
        except:
            continue        
    return pd.DataFrame(data_list)
