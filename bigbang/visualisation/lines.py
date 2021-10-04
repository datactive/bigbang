from typing import Dict, List, Optional, Tuple, Union
import numpy as np

import pylab
from colour import Color
from pylab import cm
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.pyplot import figure

from bigbang.visualisation import stackedareachart


def evolution_of_participation(
    data: dict,
    ax: mpl.axes,
    domains_of_interest: Optional[list]=None,
    percentage: bool=False,
):
    """
    Parameters
    ----------
    data : Dictionary with a format {'x_axis_labels': {'y_axis_labels': y_values}}
    domains_of_interest : 
    percentage : 
    """
    x = list(data.keys())
    ylabels = stackedareachart.get_ylabels(data)
    y = stackedareachart.data_transformation(data, percentage)
    colors = stackedareachart.create_color_palette(data, domains_of_interest)
    for iy, ylab in enumerate(ylabels):
        ax.plot(
            x, y[iy, :],
            color=colors[iy],
        )
    ax.set_xlim(np.min(x), np.max(x))
    ax.set_ylim(np.min(y), np.max(y))
    return ax

def evolution_of_graph_property_by_domain(
        data: dict,
        xkey: str,
        ykey: str,
        ax: mpl.axes,
        domains_of_interest: Optional[list]=None,
        percentile: Optional[float]=None,
):
    """
    Parameters
    ----------
        data: Dictionary create with mlist.get_domain_betweenness_centrality_per_year()
        ax:
        domains_of_interest:
        percentile:
    """
    if domains_of_interest:
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
