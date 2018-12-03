
We construct the *adjacency graph* on our set of precincts (the *nodes* of our graph)
by drawing an edge between any two VTDs that are adjacent.

.. note::
    
    An adjacency graph is different from the *dual graph* of the VTD geometries, which we would
    construct by drawing an edge between two VTDs *for each edge that they share*.
    An adjacency graph, by contrast, never has multiple edges between two nodes.


There are two concepts of "adjacency" that one can apply when constructing
an adjacency graph.

- **Rook adjacency**: Two polygons are adjacent if they share one or more *edges*.
- **Queen adjacency**: Two polygons are adjacent if they share one or more *vertices*.

All Rook edges are Queen edges, but not the other way around. Many congressional
districts are only Queen-contiguous (e.g., they consist of two polygons connected
at a single corner).

The names Rook and Queen come from the way Rook and Queen pieces in Chess_ are
allowed to move about the board.

.. _Chess: https://en.wikipedia.org/wiki/Chess

    .. note::
        The GerryChain :class:`~gerrychain.Graph` is based on the :class:`~xnetworkx.Graph`
        from the NetworkX library.
        We recommend consulting the NetworkX documentation to learn how to work with nodes, edges, and
        their attributes.
