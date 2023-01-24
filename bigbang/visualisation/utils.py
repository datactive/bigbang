from typing import Dict, List, Optional, Tuple, Union
import numpy as np

import pylab
from colour import Color
from pylab import cm
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.pyplot import figure


def create_color_palette(
    ylabels: List[str],
    domains_in_focus: Optional[List[str]] = None,
    colormap: mpl.colors.LinearSegmentedColormap = mpl.cm.jet,
    include_dof: bool = True,
    color_dof: np.array = np.array([175, 175, 175]),
    return_dict: bool = False,
) -> list:
    """
    Create colors for lines.py and stackedareachart.py

    Parameters
    ----------
        ylabels :
        domains_in_focus :
        colormap :
        color_dof :
        return_dict :
    """
    if domains_in_focus:
        if return_dict is False:
            domains_in_focus = [dof for dof in domains_in_focus if dof in ylabels]
        color_dif = colormap(np.linspace(0, 1, len(domains_in_focus)))
        if include_dof:
            if return_dict:
                colors = {}
                count = 0
                for ylab in ylabels:
                    if ylab in domains_in_focus:
                        colors[ylab] = color_dif[count]
                        count += 1
                    else:
                        colors[ylab] = (Color(rgb=(color_dof / 255)).rgb,)
            else:
                colors = []
                count = 0
                for ylab in ylabels:
                    if ylab in domains_in_focus:
                        colors.append(color_dif[count])
                        count += 1
                    else:
                        colors.append(
                            Color(rgb=(color_dof / 255)).rgb,
                        )
        else:
            if return_dict:
                colors = {ylab: col for ylab, col in zip(domains_in_focus, color_dif)}
            else:
                colors = color_dif
    else:
        colors = mpl.cm.jet(np.linspace(0, 1, len(ylabels)))
        if return_dict:
            colors = {ylab: col for ylab, col in zip(ylabels, colors)}
    return colors
