from typing import Dict, List, Optional, Tuple, Union
import numpy as np

import pylab
from colour import Color
from pylab import cm
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.pyplot import figure


def evolution_of_graph_property_by_domain(
        data: dict,
        xkey: str,
        ykey: str,
        ax: mpl.axes,
        domains_of_interest: Optional[list]=None,
        percentile: Optional[float]=None,
):
    """
    Args:
        data: Dictionary create with mlist.get_domain_betweenness_centrality_per_year()
        ax:
        domains_of_interest:
        percentile:
    """
    if domains_of_interest is not None:
        for key, value in data.items():
            if key in domains_of_interest:
                ax.plot(
                    value[xkey], value[ykey],
                    color='w',
                    linewidth=4,
                    zorder=1,
                )
                ax.plot(
                    value[xkey], value[ykey],
                    linewidth=3,
                    label=key,
                    zorder=2,
                )
            else:
                ax.plot(
                    value[xkey], value[ykey],
                    color='grey',
                    linewidth=1,
                    zorder=0,
                )
    if percentile is not None:
        betweenness_centrality = []
        for key, value in data.items():
            betweenness_centrality += value[ykey]
        betweenness_centrality = np.array(betweenness_centrality)
        threshold = np.percentile(betweenness_centrality, percentile)
        
        for key, value in data.items():
            if any(np.array(value[ykey]) > threshold):
                ax.plot(
                    value[xkey],
                    value[ykey],
                    color='w',
                    linewidth=4,
                    zorder=1,
                )
                ax.plot(
                    value[xkey],
                    value[ykey],
                    linewidth=3,
                    label=key,
                    zorder=2,
                )
            else:
                ax.plot(
                    value[xkey],
                    value[ykey],
                    color='grey',
                    linewidth=1,
                    zorder=0,
                )
    return ax
