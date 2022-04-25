from typing import Dict, List, Optional, Tuple, Union
import networkx as nx
import numpy as np

import pylab
from colour import Color
from pylab import cm
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.pyplot import figure


def edge_thickness(
    graph,
    entity_in_focus: Optional[List[str]] = None,
    exponent: float = 1,
) -> dict:
    """
    Change the thickness of edges of a networkx graph, to make the entire
    network or a selection therefore clearly visible.

    Parameters
    ----------
    graph : A networkx graph calss (such as nx.DiGraph).
    entity_in_focus : A list of domain names (e.g. huawei.com, nokia.com),
        of which the edges will be highlighted while the
        entities-out-of-focused will be greyed out.
    """
    edges, weights = zip(*nx.get_edge_attributes(graph, "weight").items())
    _edges = []
    _weights = []
    if entity_in_focus:
        for edg, wei in zip(edges, weights):
            if (edg[0] in entity_in_focus) or (edg[1] in entity_in_focus):
                _edges.append(edg)
                _weights.append(wei)
    else:
        for edg, wei in zip(edges, weights):
            _edges.append(edg)
            _weights.append(wei)
    edges = tuple(_edges)
    weights = np.power(np.array(list(_weights)), exponent)
    mapping = {edge: weight for edge, weight in zip(edges, weights)}
    return mapping


def node_size(graph):
    """
    Use the betweenness centrality to enlarge important nodes in a networkx graph.

    Parameters
    ----------
    graph : A networkx graph calss (such as nx.DiGraph).
    """
    adj = nx.betweenness_centrality(graph)
    return np.array([x * 1e3 for x in adj.values()])


def contract_nodes_by_attribute(
    dg: nx.DiGraph,
    node_attributes: Dict[str, List],
) -> nx.DiGraph:
    attribute_of = {
        name: att["node_attribute"] for name, att in dg.nodes(data=True)
    }
    same_attribute = lambda u, v: attribute_of[u] == attribute_of[v]
    dg = nx.quotient_graph(dg, same_attribute)

    mapping = {}
    for node in list(dg.nodes()):
        node_domain = list(node)[0]
        if node_domain in node_attributes["node_name"]:
            node_attribute = node_attributes["node_attribute"][
                node_attributes["node_name"].index(node_domain)
            ]
            mapping[node] = node_attribute
        else:
            mapping[node] = "Unkown"
    return nx.relabel_nodes(dg, mapping)
