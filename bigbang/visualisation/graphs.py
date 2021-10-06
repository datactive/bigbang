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


def edge_thickness(graph, domains_of_interest: list):
    """
    Parameters
    ----------
        graph : 
        domains_of_interest : 
    """
    edges, weights = zip(*nx.get_edge_attributes(graph, 'weight').items())
    _edges = []
    _weights = []
    for edg, wei in zip(edges, weights):
        if (edg[0] in domains_of_interest) or (edg[1] in domains_of_interest):
            _edges.append(edg)
            _weights.append(wei)
    edges = tuple(_edges)
    weights = np.sqrt(np.array(list(_weights)))
    return edges, weights


def node_size(graph):
    adj = nx.betweenness_centrality(graph)
    return np.array([x*1e3 for x in adj.values()])
