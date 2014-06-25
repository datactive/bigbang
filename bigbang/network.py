import parse
import networkx as nx
import matplotlib.pyplot as plt
from pprint import pprint as pp

fn = "archives/numpy-discussion/2001-November.txt"

messages = parse.open_mail_archive(fn)

def messages_to_graph(messages):

    G = nx.DiGraph()

    for m in messages:
        print parse.clean_mid(m.get('Message-ID'))
        mid = parse.clean_mid(m.get('Message-ID'))

        G.add_node(mid)
        G.node[mid]['From'] = m.get('From')
        #G.node[mid]['Date'] = m.get('Date')
        #G.node[mid]['Message'] = m.get('Message')
    
        # references should be recoverable from in-reply-to structure
        #if 'References' in d:
        #    G.add_edge(mid,d['References'])

        if 'In-Reply-To' in m:
            G.add_edge(mid,m.get('In-Reply-To'))

    return G

G = messages_to_graph(messages)

nx.write_dot(G,"mails.dot")

#nx.draw_shell(G)
#plt.show()
#nx.write_gml(G,"mails.gml")

#pp(G.nodes(data=True))
