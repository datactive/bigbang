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
    domains_of_interest: Optional[List[str]]=None,
    colormap: mpl.colors.LinearSegmentedColormap=mpl.cm.jet,
    color_default: np.array=np.array([175, 175, 175]),
) -> list:
    # find domains_of_interest in ylabels
    domains_of_interest = [doi for doi in domains_of_interest if doi in ylabels]
    # get colors
    if domains_of_interest:
        doi_colors = colormap(np.linspace(0, 1, len(domains_of_interest)))
        colors = []
        count = 0
        for ylab in ylabels:
            if ylab in domains_of_interest:
                colors.append(doi_colors[count])
                count += 1
            else:
                colors.append(
                    Color(rgb=(color_default/255)).rgb,
                )
    else:
        colors = mpl.cm.jet(np.linspace(0, 1, len(ylabels)))
    return colors
