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
    AtoB = exchanges[exchanges['From_original']==A]
    AtoB = AtoB[AtoB['From_response']==B]
    BtoA = exchanges[exchanges['From_original']==B]
    BtoA = BtoA[BtoA['From_response']==A]
    return max(max(AtoB['Date']), max(BtoA['Date'])) - min(min(AtoB['Date']), min(BtoA['Date']))
    
def num_replies(exchanges, A, B):
    AtoB = exchanges[exchanges['From_original']==A]
    AtoB = AtoB[AtoB['From_response']==B]
    BtoA = exchanges[exchanges['From_original']==B]
    BtoA = BtoA[BtoA['From_response']==A]
    return (len(AtoB), len(BtoA))
    
def reciprocity(exchanges, A, B):
    num = num_replies(exchanges, A, B)
    return float(min(num))/max(num)
