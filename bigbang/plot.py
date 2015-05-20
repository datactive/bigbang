import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def stack(df,partition=None,smooth=1,figsize=(12.5, 7.5),time=True,cm=plt.cm.Set1):
    """
    Plots a stackplot based on a dataframe. Includes support for partitioning
    and convolution.

    df - a dataframe
    partition - a (dictionary or list) of lists of columns of df
              - if dictionary, keys are used as labels
    smooth - an integer amount of convolution
    """

    # partitioning logic
    if partition is None:
        #every column stacked separately
        partition = [[c] for c in df.columns]


    if isinstance(partition,list):
        partition = enumerate(partition)
    else:
        partition = partition.items()
    
    # if an item in the portition is not in the dataframe,
    # clean it up
    partition = [(kv[0],[i for i in kv[1] if i in df.columns])
                 for kv in partition]
    # remove empty partitions
    partition = [kv for kv in partition if kv[1]]

    #convolution logic
    convolve_array = np.array([1. / smooth] * smooth)

    part_d = [np.convolve(df.as_matrix(part[1]).sum(1),
                          convolve_array,
                          mode='same')
                 for part in partition]

    d = np.row_stack(part_d)

    fig,ax = plt.subplots(figsize=figsize)

    #colors = [cm(float(k) / len(partition)) for k in range(len(partition))]
    colors = cm(np.linspace(0,1,num=len(partition)))

    stacks = ax.stackplot(df.index,d,linewidth=0,colors=colors)

    # time axes
    if time:
        fig.axes[0].xaxis_date()

    # legend
    # make proxy artists
    proxy_rects = [Rectangle((0, 0), 1, 1, fc=pc.get_facecolor()[0]) for pc in stacks]
    # make the legend
    ax.legend(proxy_rects,[kv[0] for kv in partition])

    plt.show()
