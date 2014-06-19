import parse
import networkx as nx
from pprint import pprint as pp

fn = "archives/numpy-discussion/2001-November.txt"

mails = parse.open_mail_archive(fn)

dicts = [parse.mail_to_dict(m) for m in mails]

G = nx.DiGraph()

for d in dicts:

    #pp(d)

    mid = d['Message-ID']

    G.add_node(mid)
    G.node[mid]['From'] = d['From']
    G.node[mid]['Date'] = d['Date']
    G.node[mid]['Message'] = d['Message']
    
    if 'References' in d:
        G.add_edge(mid,d['References'])

    if 'In-Reply-To' in d:
        G.add_edge(mid,d['In-Reply-To'])

nx.write_gexf(G,"mails.gexf")

#pp(G.nodes(data=True))
