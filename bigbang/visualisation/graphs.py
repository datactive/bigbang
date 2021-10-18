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


def edge_thickness(graph, entity_in_focus: list):
    """
    Parameters
    ----------
        graph :
        entity_in_focus :
    """
    edges, weights = zip(*nx.get_edge_attributes(graph, "weight").items())
    _edges = []
    _weights = []
    for edg, wei in zip(edges, weights):
        if (edg[0] in entity_in_focus) or (edg[1] in entity_in_focus):
            _edges.append(edg)
            _weights.append(wei)
    edges = tuple(_edges)
    weights = np.sqrt(np.array(list(_weights)))
    return edges, weights


def node_size(graph):
    adj = nx.betweenness_centrality(graph)
    return np.array([x * 1e3 for x in adj.values()])
