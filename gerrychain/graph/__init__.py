"""
This module implements the Graph class that is used
by GerryChain code.

It exposes standard graph functionality for a dual-graph
containing nodes and edges.  Both nodes and edges can have
data associated with them.

A Graph object is typically created by first creating
a NetworkX.Graph object and then converting it to
a GerryChain Graph object using from_networkx().

For instance:

    import networkx
    from gerrychain import Graph

    # Create a NetworkX graph
    nx_graph = networkx.Graph()
    nx_graph.add_edges_from(...)

    # Create a GerryChain graph from the NetworkX graph
    my gerrychain_graph = Graph.from_networkx(nx_graph)

Internally, a Graph object contains and embedded graph
object based either on NetworkX or RustworkX.  After
creating a Partition object in GerryChain, the embedded
graph object is converted to be based on RustworkX (for
performance reasons).
"""

from .adjacency import *
from .geo import *
from .graph import *
