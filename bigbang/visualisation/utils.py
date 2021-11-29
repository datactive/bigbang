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
    entity_in_focus: Optional[List[str]] = None,
    colormap: mpl.colors.LinearSegmentedColormap = mpl.cm.jet,
    include_eif: bool = True,
    color_dof: np.array = np.array([175, 175, 175]),
    return_dict: bool = False,
) -> list:
    """
    Create colors for lines.py and stackedareachart.py

    Parameters
    ----------
        ylabels :
        entity_in_focus :
        colormap :
        color_dof :
        return_dict :
    """
    if entity_in_focus:
        if return_dict is False:
            entity_in_focus = [
                eif for eif in entity_in_focus if eif in ylabels
            ]
        color_eif = colormap(np.linspace(0, 1, len(entity_in_focus)))
        if include_eif:
            if return_dict:
                colors = {}
                count = 0
                for ylab in ylabels:
                    if ylab in entity_in_focus:
                        colors[ylab] = color_eif[count]
                        count += 1
                    else:
                        colors[ylab] = (Color(rgb=(color_eif / 255)).rgb,)
            else:
                colors = []
                count = 0
                for ylab in ylabels:
                    if ylab in entity_in_focus:
                        colors.append(color_eif[count])
                        count += 1
                    else:
                        colors.append(
                            Color(rgb=(color_eif / 255)).rgb,
                        )
        else:
            if return_dict:
                colors = {
                    ylab: col for ylab, col in zip(entity_in_focus, color_eif)
                }
            else:
                colors = color_eif
    else:
        colors = mpl.cm.jet(np.linspace(0, 1, len(ylabels)))
        if return_dict:
            colors = {ylab: col for ylab, col in zip(ylabels, colors)}
    return colors
