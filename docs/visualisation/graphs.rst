Graphs
======

To help visualise the results obtained in :ref:`Communication Network <communication_network>`,
we provide support functions, such that the thickness of graph edges and nodes
can be adjusted. Assuming that one as already executed the
``mlist.create_sender_receiver_digraph()`` command, we can use
``graphs.edge_thickness()`` to highlight the relation between specific actors or
``graphs.node_size()`` to let the node size increase with their betweenness centrality.

.. code-block:: python

    import networkx as nx
    from bigbang.visualisation import graphs

    edges, edge_width = graphs.edge_thickness(
        mlist.dg,
        entity_in_focus=['t-mobile.at', 'nokia.com'],
    )
    node_size = graphs.node_size(mlist.dg)

    nx.draw_networkx_nodes(
        mlist.dg, pos,
        node_size=node_size,
    )

    nx.draw_networkx_edges(
        mlist.dg, pos,
        width=edge_width,
        edgelist=edges,
        edge_color=edge_width,
        edge_cmap=plt.cm.rainbow,
    )
