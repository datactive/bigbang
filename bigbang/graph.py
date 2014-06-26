import parse
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

    replies = [m for m in messages if 'In-Reply-To' in m]

    for m in replies:
        m_from = parse.clean_from(m.get('From'))
        reply_to_mid = m.get('In-Reply-To')

        if reply_to_mid in from_dict:
            m_to = from_dict[reply_to_mid]

            reply_counts[m_from][m_to] = reply_counts[m_from].get(m_to,0) + 1

            IG.add_edge(m_from,m_to)
        else:
            print reply_to_mid + " not in archive"

    pp(sender_counts)
    pp(reply_counts)

    return IG
