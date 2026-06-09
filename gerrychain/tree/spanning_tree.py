import random
from typing import (
    Dict,
    Optional,
)

from ..graph import Graph

"""
This module provides two implementation of spanning tree functions:
uniform_spanning_tree() and random_spanning_tree().

A spanning tree is a tree formed from a connected undirected graph that contains
all of the nodes in the graph, but only some of the edges, so that the resulting
graph is a tree (with no cycles). You can learn more here:

    https://en.wikipedia.org/wiki/Spanning_tree

Given a spanning tree for a graph, one can easily compute the population of every
subtree by doing a bottom up tree traversal.  Given the population totals for
every subtree, one can carve off subtrees that have the desired population, one
by one, and thereby construct a set of districts (note that this can fail if
the population of a subtree is below epsilon of the population target and
the parent subtree is above epsilon).

Two two implementations are:

    uniform_spanning_tree() - a uniform spanning tree:

        A spanning tree that is chosen randomly from among all possible
        spanning trees with equal probability is called a uniform spanning
        tree. Wilson's algorithm can be used to generate uniform spanning
        trees in polynomial time by a process of taking a random walk on
        the given graph and erasing the cycles created by this walk.
        uniform_spanning_tree() implements Wilson's algorithm.

    random_spanning_tree() - a minimum spanning tree (MST):

        Unlike a uniform spanning tree, an MST selects a spanning tree from
        a subset of all spanning trees, based on edge weights.  It selects
        a spanning tree that minimizes the total of all of the edge weights
        in the graph.

        In GerryChain, the random_spanning_tree() function implements an
        MST using Kruksal's Algorithm with random weights.  That is,
        the code associates a random weight (between 0 and 1) to each
        edge in the graph and then computes the MST for those weights.

        The random_spanning_tree() function additionally supports
        a "region surcharge" that increases the weights for specific
        edges.  This allows one to construct a spanning tree that
        tends to keep the nodes of some edges together in the same
        district.  The details are documented elsewhere - the point
        here is that the random_spanning_tree() function is the one
        you want to use if you want to bias the outcome to keep some
        nodes together in the resulting district plan (for instance
        nodes that are in the same county).

        You can learn more about MST's here:

            https://en.wikipedia.org/wiki/Minimum_spanning_tree

Note that the uniform_spanning_tree() function selects "uniformly"
from the space of possible spanning trees, and minimum
spanning trees do NOT. So depending on your target distribution, you
might prefer one spanning tree function vs. the other.

Key functionalities include:

- Implementation of random and uniform spanning trees for graph partitioning.

Dependencies:

- random: Provides random number generation for probabilistic approaches.
- typing: Used for type hints.

"""

"""
frm: RX Documentation:

As far as I can tell a spanning tree is only ever used to populate a _PopulatedGraph
and so, there is no need to worry about translating the spanning tree's nodes into
the context of the parent.  Stated differently, a spanning tree is not used to
compute something about a subgraph but rather to compute something about whatever
graph is currently being dealt with.

In short, I am assuming that we can ignore the fact that RX subgraphs have different
node_ids for this function and all will be well...
"""


def random_spanning_tree(graph: Graph, region_surcharge: Optional[Dict] = None) -> Graph:
    """Builds a minimum spanning tree chosen by Kruskal's method using random weights.

    The region_surcharge parameter allows the caller to bias the selection of edges by increasing
    the weights of some edges. For example, if you specify a region surcharge for "county", then
    all edges whose nodes do NOT have the same non-null value for "county" will have a surcharge
    added to that edge. This will have the effect of biasing the algorithm to preferentially select
    nodes that belong to the same county.

    Kruskal's method chooses the edges with the lowest weight first, so edges with high weights
    will be selected last - with the highest weights not chosen at all (once all the nodes are in
    the tree, the algorithm stops adding edges).

    If no region_surcharges are provided, then the algorithm just randomly specifies the weights of
    all edges before generating an MST which is essentially a random spanning_tree generator. In
    this case, the caller could have instead used the uniform_spanning_tree() function. The
    performance difference between uniform_spanning_tree() and random_spanning_tree() depends on
    the structure of the graph.

    In short, if you want to bias the selection of districts to keep some nodes together, you want
    to use this routine, random_spanning_tree().

    Note that the random weights applied to edges have values between 0 and 1 so the additional
    weights supplied in the region_surcharge should be sized appropriately. If the region_surcharge
    weight is greater than 1, then it will be heavier than any other edge that has not had a
    surcharge applied to it.

    Args:
        graph (Graph): The input graph to build the spanning tree from.
        region_surcharge (Optional[Dict], optional): Dictionary of surcharges to add to the random
            weights used in region-aware variants.

    Returns:
        Graph: The maximal spanning tree represented as a GerryChain Graph.
    """

    # Create an empty dict now instead of as a default parameter to avoid
    # having a single dict instantiated at program start time that is
    # reused for all calls.
    if region_surcharge is None:
        region_surcharge = dict()

    # Add a random weight to each edge in the graph with the goal of
    # causing the selection of a different (random) spanning tree based
    # on those weights.  Note that the value of this random weight
    # will be between 0 and 1.
    #
    # If a region_surcharge was passed in, then add the
    # appropriate region_surcharge value to the weight for those
    # edges that are NOT in the region.
    #
    if not region_surcharge:
        # Performance fast path (no region surcharge - the common case):
        #
        # The edge endpoints are only needed to compute region surcharges, so
        # when there are none we can skip the per-edge get_edge_from_edge_id()
        # lookup entirely and just assign a random weight to every edge.  This
        # loop runs once per spanning tree, and chains with a tight population
        # tolerance draw many spanning trees per step, so this matters.
        for edge_id in graph.edge_indices:
            graph.edge_data(edge_id)["random_weight"] = random.random()
    else:
        for edge_id in graph.edge_indices:
            edge = graph.get_edge_from_edge_id(edge_id)
            weight = random.random()

            # If there are any entries in the region_surcharge dict, then add
            # additional weight to the edge if the nodes in the edge are not
            # in the same "region", that is:
            #
            #    * if one of the nodes is NOT in a region (for instance in the
            #      case of a "municipality" region defined by the key "muni",
            #      the node was not in any municpality and hence there was no
            #      node_data for the atrribute, "muni")
            #
            #    * or if the nodes were in different "regions"
            #
            for key, value in region_surcharge.items():
                # We surcharge edges that are in different regions and those that are not in any region
                node_id1 = edge[0]
                node_id2 = edge[1]
                node_id1_region = graph.node_data(node_id1)[key]
                node_id2_region = graph.node_data(node_id2)[key]
                if (
                    node_id1_region != node_id2_region
                    or node_id1_region is None
                    or node_id2_region is None
                ):
                    weight += value

            graph.edge_data(edge_id)["random_weight"] = weight

    graph.verify_graph_is_valid()

    minimum_spanning_tree = graph.minimum_spanning_tree_from_edge_weight(
        edge_weight_attribute_name="random_weight"
    )
    return minimum_spanning_tree


def uniform_spanning_tree(
    graph: Graph,
    region_surcharge: dict = None,  # accepted for API compatibility, but unused
) -> Graph:
    """Builds a spanning tree chosen uniformly from the space of all spanning trees of the graph.

    Uses Wilson's algorithm. If interested, there is a nice animated description of Wilson's
    algorithm here:

    https://weblog.jamisbuck.org/2011/1/20/maze-generation-wilson-s-algorithm

    A brief description of Wilson's Alorithm follows:

    Pick a node at random for the root node of the spanning tree. Then pick any other node and do a
    random walk until you end up at the root node, but as you go remember the last move you made at
    each node - which will overwrite any previous move. When you end up at the root node, go back
    to the starting node and follow the path left behind, which will cleverly contain no cycles
    because the paths for any cycles were overwritten.

    Add the nodes in the path (remembering child and parent) to the list of nodes you have added to
    the tree. Then pick another node at random that is not already in the tree and do another
    random walk, ending when you fall on a node already in the tree. Then add the nodes for that
    random walk to the tree.

    Rinse and repeat until all nodes have been added to the tree.

    Args:
        graph (Graph): Graph
        region_surcharge (Optional[Dict], optional): Not used in this function.  It exists
            in the function signature so that all spanning tree functions will share the
            same signature.

    Returns:
        Graph: A spanning tree of the graph chosen uniformly at random.
    """

    if region_surcharge:
        raise ValueError("uniform_spanning_tree() region_surcharge paramter should be empty")

    # Pick a starting point at random
    root_id = random.choice(list(graph.node_indices))

    # Initiallize the tree to contain the root_node (with no parent)
    tree_nodes = set([root_id])
    parent_node_id = {root_id: None}

    for node_id in graph.node_indices:

        # Random walk (perhaps with cycles) that records the
        # last path taken before hitting a node already in
        # tree_nodes.  Note that recording the last path
        # taken effectively removes cycles from the path.
        u = node_id
        while u not in tree_nodes:
            parent_node_id[u] = random.choice(list(graph.neighbors(u)))
            u = parent_node_id[u]

        # Record the "direct" path (the one with no cycles)
        # from the starting node, u, to a node already
        # in tree_nodes.
        u = node_id
        while u not in tree_nodes:
            tree_nodes.add(u)
            u = parent_node_id[u]

    graph_of_spanning_tree = Graph.from_null_networkx()
    nx_graph = graph_of_spanning_tree.get_nx_graph()

    for node_id in tree_nodes:
        if parent_node_id[node_id] is not None:
            # Add the nodes and the edge to the spanning_tree
            nx_graph.add_edge(node_id, parent_node_id[node_id])

    # Return a graph that is the same "kind" of graph as the graph passed in.
    # The current graph_of_spanning_tree is an NX-based graph, so convert it to
    # be RX-based if the graph passed in was RX-based.
    #
    if graph.is_rx_graph():
        graph_of_spanning_tree = graph_of_spanning_tree.convert_from_nx_to_rx()

    return graph_of_spanning_tree
