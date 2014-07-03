import parse
import math
import numpy as np
import networkx as nx
#import matplotlib.pyplot as plt
from pprint import pprint as pp
from collections import Counter


def messages_to_reply_graph(messages):

    G = nx.DiGraph()

    for m in messages:
        mid = parse.clean_mid(m.get('Message-ID'))

        G.add_node(mid)
        G.node[mid]['From'] = m.get('From')
        #G.node[mid]['Date'] = m.get('Date')
        #G.node[mid]['Message'] = m.get('Message')
    
        # references should be recoverable from in-reply-to structure
        #if 'References' in d:
        #    G.add_edge(mid,d['References'])

        if 'In-Reply-To' in m:
            G.add_edge(mid,parse.clean_mid(m.get('In-Reply-To')))

    return G

def messages_to_interaction_graph(messages):
    
    IG = nx.DiGraph()

    from_dict = {}

    sender_counts = {}
    reply_counts = {}

    for m in messages:
        m_from = parse.clean_from(m.get('From'))
        from_dict[m.get('Message-ID')] = m_from
        sender_counts[m_from] = sender_counts.get(m_from,0) + 1
        # the necessity of this initialization step may be dubious
        reply_counts[m_from] = reply_counts.get(m_from,{})
        IG.add_node(m_from)

    for sender,count in sender_counts.items():
        IG.node[sender]['sent'] = count

    replies = [m for m in messages if 'In-Reply-To' in m]

    for m in replies:
        m_from = parse.clean_from(m.get('From'))
        reply_to_mid = m.get('In-Reply-To')

        if reply_to_mid in from_dict:
            m_to = from_dict[reply_to_mid]
            reply_counts[m_from][m_to] = reply_counts[m_from].get(m_to,0) + 1
        else:
            print reply_to_mid + " not in archive"

    for m_from, edges in reply_counts.items():
        for m_to, count in edges.items():
            IG.add_edge(m_from,m_to,weight=count)


    return IG

# Ulanowicz ecosystem health measures
# input is weighted adjacency matrix
def ascendancy(am):
    #total system throughput
    tst = np.sum(am)

    # should these be normalized?!?!
    #output rates
    s0 = np.tile(np.sum(am,0).T,(am.shape[0],1))
    #input rates
    s1 = np.tile(np.sum(am,1).T,(am.shape[1],1)).T

    logs = np.nan_to_num(np.log(am * np.sum(am) / (s0 * s1)))

    #ascendancy!
    A = np.sum(am * logs)

    return A

def capacity(am):
    # total system throughput
    tst = np.sum(am)

    logs = np.nan_to_num(np.log(am / tst))

    return - np.sum(am * logs)

def overhead(am):
    #could be more efficient...
    return capacity(am) - ascendancy(am)
