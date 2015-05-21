from . import parse
import math
import numpy as np
import networkx as nx
import bigbang.process as process
# import matplotlib.pyplot as plt
from pprint import pprint as pp
from collections import Counter
import pandas


def messages_to_reply_graph(messages):

    G = nx.DiGraph()

    for m in messages:
        mid = parse.clean_mid(m.get('Message-ID'))

        G.add_node(mid)
        G.node[mid]['From'] = m.get('From')
        # G.node[mid]['Date'] = m.get('Date')
        # G.node[mid]['Message'] = m.get('Message')

        # references should be recoverable from in-reply-to structure
        # if 'References' in d:
        #    G.add_edge(mid,d['References'])

        if 'In-Reply-To' in m:
            G.add_edge(mid, parse.clean_mid(m.get('In-Reply-To')))

    return G


def messages_to_interaction_graph(messages, verbose=False):

    IG = nx.DiGraph()

    from_dict = {}

    sender_counts = {}
    reply_counts = {}

    if not isinstance(messages, pandas.core.frame.DataFrame):
        df = process.messages_to_dataframe(messages)
    else:
        df = messages

    for m in df.iterrows():
        m_from = parse.clean_from(m[1]['From'])
        from_dict[m[0]] = m_from
        sender_counts[m_from] = sender_counts.get(m_from, 0) + 1
        # the necessity of this initialization step may be dubious
        reply_counts[m_from] = reply_counts.get(m_from, {})
        IG.add_node(m_from)

    for sender, count in sender_counts.items():
        IG.node[sender]['sent'] = count

    replies = [m for m in df.iterrows() if m[1]['In-Reply-To'] is not None]

    for m in replies:
        m_from = parse.clean_from(m[1]['From'])
        reply_to_mid = m[1]['In-Reply-To']

        if reply_to_mid in from_dict:
            m_to = from_dict[reply_to_mid]
            reply_counts[m_from][m_to] = reply_counts[m_from].get(m_to, 0) + 1
        else:
            if verbose:
                print reply_to_mid + " not in archive"

    for m_from, edges in reply_counts.items():
        for m_to, count in edges.items():
            IG.add_edge(m_from, m_to, weight=count)

    return IG


# turn an interaction graph into a weighted edge matrix
def interaction_graph_to_matrix(dg):
    nodes = dg.nodes()

    n_nodes = len(nodes)

    # n x n where n is number of nodes
    matrix = np.zeros([n_nodes, n_nodes])

    for m_from, m_to, data in dg.edges(data=True):
        i = nodes.index(m_from)
        j = nodes.index(m_to)

        matrix[i, j] = data['weight']

    return matrix


# Ulanowicz ecosystem health measures
# input is weighted adjacency matrix
def ascendancy(am):
    # total system throughput
    tst = np.sum(am)

    # should these be normalized?!?!
    # output rates
    s0 = np.tile(np.sum(am, 0).T, (am.shape[0], 1))
    # input rates
    s1 = np.tile(np.sum(am, 1).T, (am.shape[1], 1)).T

    logs = np.nan_to_num(np.log(am * np.sum(am) / (s0 * s1)))

    # ascendancy!
    A = np.sum(am * logs)

    return A


def capacity(am):
    # total system throughput
    tst = np.sum(am)

    logs = np.nan_to_num(np.log(am / tst))

    return - np.sum(am * logs)


def overhead(am):
    # could be more efficient...
    return capacity(am) - ascendancy(am)


""" copied from process.py may have bugs"""


def compute_ascendancy(messages, duration=50):
    print('compute ascendancy')
    dated_messages = {}

    for m in messages:
        d = get_date(m)

        if d is not None and d < datetime.datetime.now(pytz.utc):
            o = d.toordinal()
            dated_messages[o] = dated_messages.get(o, [])
            dated_messages[o].append(m)

    days = [k for k in dated_messages.keys()]
    day_offset = min(days)
    epoch = max(days) - min(days)

    ascendancy = np.zeros([max(days) - min(days) + 1])
    capacity = np.zeros(([max(days) - min(days) + 1]))

    for i in range(epoch):
        min_d = min(days) + i
        max_d = min_d + duration

        block_messages = []

        for d in range(min_d, max_d):
            block_messages.extend(dated_messages.get(d, []))

        b_IG = graph.messages_to_interaction_graph(block_messages)
        b_matrix = graph.interaction_graph_to_matrix(b_IG)

        ascendancy[min_d - day_offset] = graph.ascendancy(b_matrix)
        capacity[min_d - day_offset] = graph.capacity(b_matrix)

    return ascendancy, capacity
