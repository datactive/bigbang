import matplotlib.patches as patches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


def stack(
    df,
    partition=None,
    smooth=1,
    figsize=(12.5, 7.5),
    time=True,
    cm=plt.cm.Set1,
):
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
        # every column stacked separately
        partition = [[c] for c in df.columns]

    if isinstance(partition, list):
        partition = enumerate(partition)
    else:
        partition = list(partition.items())

    # if an item in the portition is not in the dataframe,
    # clean it up
    partition = [
        (kv[0], [i for i in kv[1] if i in df.columns]) for kv in partition
    ]
    # remove empty partitions
    partition = [kv for kv in partition if kv[1]]

    # convolution logic
    convolve_array = np.array([1.0 / smooth] * smooth)

    part_d = [
        np.convolve(df.as_matrix(part[1]).sum(1), convolve_array, mode="same")
        for part in partition
    ]

    d = np.row_stack(part_d)

    fig, ax = plt.subplots(figsize=figsize)

    # colors = [cm(float(k) / len(partition)) for k in range(len(partition))]
    colors = cm(np.linspace(0, 1, num=len(partition)))

    stacks = ax.stackplot(df.index, d, linewidth=0, colors=colors)

    # time axes
    if time:
        fig.axes[0].xaxis_date()

    # legend
    # make proxy artists
    proxy_rects = [
        patches.Rectangle((0, 0), 1, 1, fc=pc.get_facecolor()[0])
        for pc in stacks
    ]
    # make the legend
    ax.legend(proxy_rects, [kv[0] for kv in partition])

    plt.show()


# modified from http://sociograph.blogspot.com/2012/11/visualizing-adjacency-matrices-in-python.html
def draw_adjacency_matrix(
    G, node_order=None, partitions=[], colors=[], cmap="Greys", figsize=(6, 6)
):
    """
    - G is a networkx graph
    - node_order (optional) is a list of nodes, where each node in G
          appears exactly once
    - partitions is a list of node lists, where each node in G appears
          in exactly one node list
    - colors is a list of strings indicating what color each
          partition should be
    If partitions is specified, the same number of colors needs to be
    specified.
    """
    adjacency_matrix = nx.to_numpy_matrix(
        G, dtype=np.bool, nodelist=node_order
    )

    plt.figure(figsize=figsize)  # in inches
    plt.imshow(adjacency_matrix, cmap=cmap, interpolation="none")

    # The rest is just if you have sorted nodes by a partition and want to
    # highlight the module boundaries
    assert len(partitions) == len(colors)
    ax = plt.gca()
    current_idx = 0
    for partition, color in zip(partitions, colors):
        # for module in partition:
        ax.add_patch(
            patches.Rectangle(
                (current_idx, current_idx),
                len(partition),  # Width
                len(partition),  # Height
                facecolor="none",
                edgecolor=color,
                linewidth="1",
            )
        )
        current_idx += len(partition)
