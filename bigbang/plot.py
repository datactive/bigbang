import numpy as np
import matplotlib.pyplot as plt

def stack(df,partition=None,smooth=1,figsize=(12.5, 7.5),time=True):

    if partition is None:
        #every column stacked separately
        partition = [[c] for c in df.columns]

    convolve_array = np.array([1. / smooth] * smooth)

    part_d = [np.convolve(df.as_matrix(part).sum(1),convolve_array,mode='same')
                 for part in partition.values()]

    d = np.row_stack(part_d)

    fig = plt.figure(figsize=figsize)

    plt.stackplot(df.index,d,linewidth=0)

    if time:
        fig.axes[0].xaxis_date()

    plt.show()
