from typing import Dict, List, Optional, Tuple, Union
import numpy as np

import pylab
from colour import Color
from pylab import cm
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.pyplot import figure


def get_ylabels(data) -> List[str]:
    ylabels = list(set([
        ykey
        for ydic in data.values()
        for ykey in ydic.keys()
    ]))
    return ylabels

def data_transformation(idata: dict, percentage: bool=False) -> np.ndarray:
    """
    Returns
    -------
    odata : array with the format (# of ylabels, # of xlabels)
    """
    # collect all ylabels
    ylabels = get_ylabels(idata)
    # create numpy array and fill sparse matrix
    odata = np.zeros((len(ylabels), len(idata.keys())))
    for iy, ylab in enumerate(ylabels):
        for ix, ydic in enumerate(idata.values()):
            if ylab in list(ydic.keys()):
                odata[iy, ix] = ydic[ylab]
    if percentage:
        odata = odata / np.sum(odata, axis=0)
    return odata

def create_color_palette(
    data: dict, domains_of_interest: Optional[List[str]]=None,
) -> list:
    # collect all ylabels
    ylabels = get_ylabels(data)
    # find domains_of_interest in ylabels
    domains_of_interest = [doi for doi in domains_of_interest if doi in ylabels]
    # get colors
    if domains_of_interest:
        doi_colors = mpl.cm.jet(np.linspace(0, 1, len(domains_of_interest)))
        colors = []
        count = 0
        for ylab in ylabels:
            if ylab in domains_of_interest:
                colors.append(doi_colors[count])
                count += 1
            else:
                colors.append(
                    Color(rgb=(np.array([175, 175, 175])/255)).rgb,
                )
    else:
        colors = mpl.cm.jet(np.linspace(0, 1, len(ylabels)))
    return colors

def stacked_area_chart(
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
    y = data_transformation(data, percentage)
    colors = create_color_palette(data, domains_of_interest)
    ax.stackplot(
        x, y,
        colors=colors,
    )
    ax.set_xlim(np.min(x), np.max(x))
    ax.set_ylim(np.min(y), np.max(y))
    return ax
