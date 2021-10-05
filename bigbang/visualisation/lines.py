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
from bigbang.visualisation import utils


def evolution_of_participation_1D(
    data: dict,
    ax: mpl.axes,
    domains_in_focus: Optional[list] = None,
    percentage: bool = False,
    colormap: mpl.colors.LinearSegmentedColormap = mpl.cm.jet,
) -> mpl.axes:
    """
    Parameters
    ----------
    data : Dictionary with a format {'x_axis_labels': {'y_axis_labels': y_values}}
    domains_in_focus :
    percentage :
    """
    x = list(data.keys())
    ylabels = stackedareachart.get_ylabels(data)
    y = stackedareachart.data_transformation(data, ylabels, percentage)
    colors = utils.create_color_palette(
        ylabels,
        domains_in_focus,
        colormap,
        include_dof=False,
        return_dict=True,
    )
    for iy, ylab in enumerate(ylabels):
        if ylab in domains_in_focus:
            ax.plot(
                x,
                y[iy, :],
                color="w",
                linewidth=4,
                zorder=1,
            )
            ax.plot(
                x,
                y[iy, :],
                color=colors[ylab],
                linewidth=3,
                zorder=1,
                label=ylab,
            )
        else:
            ax.plot(
                x,
                y[iy, :],
                color="grey",
                linewidth=1,
                zorder=0,
                alpha=0.2,
            )
    ax.set_xlim(np.min(x), np.max(x))
    ax.set_ylim(np.min(y), np.max(y))
    return ax


def evolution_of_participation_2D(
    xdata: dict,
    ydata: dict,
    ax: mpl.axes,
    domains_in_focus: Optional[list] = None,
    percentage: bool = False,
    colormap: mpl.colors.LinearSegmentedColormap = mpl.cm.jet,
) -> mpl.axes:
    """
    Parameters
    ----------
    data : Dictionary with a format {'x_axis_labels': {'y_axis_labels': y_values}}
    domains_in_focus :
    percentage :
    """
    # TODO: include time indication
    xlabels = stackedareachart.get_ylabels(xdata)
    ylabels = stackedareachart.get_ylabels(ydata)
    # ensure uniform order
    labels = list(set(xlabels + ylabels))
    xindx = [xlabels.index(lab) if lab in xlabels else None for lab in labels]
    xlabels = [xlabels[i] if i is not None else None for i in xindx]
    yindx = [ylabels.index(lab) if lab in ylabels else None for lab in labels]
    ylabels = [ylabels[i] if i is not None else None for i in yindx]
    # create arrays with format (# of ylabels, # of xlabels)
    x = stackedareachart.data_transformation(xdata, xlabels, percentage)
    y = stackedareachart.data_transformation(ydata, ylabels, percentage)
    colors = utils.create_color_palette(
        ylabels,
        domains_in_focus,
        colormap,
        include_dof=False,
        return_dict=True,
    )
    ax.plot([0, np.max(y)], [0, np.max(y)], c="k", linestyle="--", zorder=0)
    for i, lab in enumerate(labels):
        if lab in domains_in_focus:
            ax.plot(
                x[i, :],
                y[i, :],
                color="w",
                linewidth=4,
                zorder=1,
            )
            ax.plot(
                x[i, :],
                y[i, :],
                color=colors[lab],
                linewidth=3,
                zorder=1,
                label=lab,
            )
        else:
            ax.plot(
                x[i, :],
                y[i, :],
                color="grey",
                linewidth=1,
                zorder=0,
                alpha=0.2,
            )
    ax.set_xlim(np.min(x), np.max(x))
    ax.set_ylim(np.min(y), np.max(y))
    return ax


def evolution_of_graph_property_by_domain(
    data: dict,
    xkey: str,
    ykey: str,
    ax: mpl.axes,
    domains_in_focus: Optional[list] = None,
    percentile: Optional[float] = None,
) -> mpl.axes:
    """
    Parameters
    ----------
        data : Dictionary create with mlist.get_domain_betweenness_centrality_per_year()
        ax :
        domains_in_focus :
        percentile :
    """
    if domains_in_focus:
        for key, value in data.items():
            if key in domains_in_focus:
                ax.plot(
                    value[xkey],
                    value[ykey],
                    color="w",
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
                    color="grey",
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
                    color="w",
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
                    color="grey",
                    linewidth=1,
                    zorder=0,
                )
    return ax
