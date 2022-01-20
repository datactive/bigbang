import bigbang.parse as parse
import bigbang.analysis.graph as graph
import networkx as nx
import matplotlib.pyplot as plt
from pprint import pprint as pp

fns = [
    "archives/numpy-discussion/2011-November.txt",
    "archives/ipython-dev/2011-November.txt",
    "archives/ipython-user/2011-November.txt",
    "archives/scipy-dev/2011-November.txt",
    "archives/scipy-user/2011-November.txt",
]

mls = [parse.open_mail_archive(fn) for fn in fns]

messages = [m for ml in mls for m in ml]

# import pdb; pdb.set_trace()

RG = graph.messages_to_reply_graph(messages)

IG = graph.messages_to_interaction_graph(messages)

pdig = nx.to_pydot(IG)

pdig.set_overlap("False")

pdig.write_png("interactions.png", prog="neato")

nx.write_gml(IG, "interactions.gml")

# matplotlib visualization
pos = nx.graphviz_layout(IG, prog="neato")
node_size = [data["sent"] * 40 for name, data in IG.nodes(data=True)]

nx.draw(
    IG,
    pos,
    node_size=node_size,
    node_color="w",
    alpha=0.4,
    font_size=18,
    font_weight="bold",
)


# edge width is proportional to replies sent
edgewidth = [d["weight"] for (u, v, d) in IG.edges(data=True)]

# overlay edges with width based on weight
nx.draw_networkx_edges(IG, pos, alpha=0.5, width=edgewidth, edge_color="r")

plt.show()

nx.write_gexf(IG, "nov-11.gexf")
