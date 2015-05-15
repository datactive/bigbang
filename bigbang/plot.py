import numpy as np
import matplotlib.pyplot as plt

def stack(df,partition=None,smooth=1,figsize=(12.5, 7.5),time=True):
    """
    Plots a stackplot based on a dataframe. Includes support for partitioning
    and convolution.

    df - a dataframe
    partition - a list of lists of columns of df
    smooth - an integer amount of convolution
    """

    # partitioning logic
    if partition is None:
        #every column stacked separately
        partition = [[c] for c in df.columns]

    
    # if an item in the portition is not in the dataframe,
    # clean it up
    partition = [[i for i in p if i in df.columns]
                 for p in partition]
    # remove empty partitions
    partition = [p for p in partition if p]

    #convolution logic
    convolve_array = np.array([1. / smooth] * smooth)

    part_d = [np.convolve(df.as_matrix(part).sum(1),
                          convolve_array,
                          mode='same')
                 for part in partition]

    d = np.row_stack(part_d)

    fig = plt.figure(figsize=figsize)

    plt.stackplot(df.index,d,linewidth=0)

    # time axes
    if time:
        fig.axes[0].xaxis_date()

    plt.show()
