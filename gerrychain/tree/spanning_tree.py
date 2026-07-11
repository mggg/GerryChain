import random
from typing import (
    Dict,
    Optional,
)

from .._rng import make_rng
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


def random_spanning_tree(
    graph: Graph,
    region_surcharge: Optional[Dict] = None,
    treat_unassigned_as_single_region: bool = False,
    *,
    rng: random.Random | int | None = None,
) -> Graph:
    """Builds a minimum spanning tree chosen by Kruskal's method using random weights.

    Kruskal's method chooses the edges with the lowest weight first, so edges with high weights
    will be selected last - with the highest weights not chosen at all (once all the nodes are in
    the tree, the algorithm stops adding edges). If no ``region_surcharge`` is provided, every edge
    just gets a plain random weight, so the result is an ordinary random spanning tree.

    Region surcharge (keeping regions together):
        The ``region_surcharge`` parameter lets you bias the spanning tree - and therefore the
        districts eventually cut from it - so that a chosen kind of region (a county, municipality,
        precinct, or any other group of nodes that share a node attribute) tends to be kept whole.

        Surcharges are passed as a dict mapping a node-attribute name to a numeric surcharge, e.g.
        ``{"county": 0.5}``. For each edge, the surcharge for an attribute is added to that edge's
        random weight when the edge crosses a boundary for that attribute - that is, when the two
        endpoints do NOT share the same non-null value of the attribute. So edges *inside* a region
        keep their plain random weight, while edges on the *boundary* of a region are made heavier.

        Since this function builds a *minimum* spanning tree, making the boundary edges heavier
        biases the MST toward connecting each region through its cheap interior edges. Therefore,
        the region tends to appear as a single connected subtree of the spanning tree. Because the
        bipartition step cuts exactly one edge, a region small enough to fit inside one district then
        tends to be kept whole. A region larger than a district cannot be kept whole: it still
        has to be cut enough times to break it into district-sized pieces (a region holding roughly
        k districts' worth of population needs at least k - 1 cuts, so a populous county like Los
        Angeles must be split a dozen or more times no matter how large the surcharge). What a
        dominating surcharge buys in that case is splitting the region only as many times as its
        population forces (possibly plus 1 depending on the rest of the plan), rather than carving
        it up arbitrarily.

        Choosing surcharge values: the random weights are drawn uniformly from ``[0, 1)``, so the
        surcharge should be sized relative to that range. A surcharge well below 1 is a *soft* bias
        that competes with the random weights (regions are kept together more often, but not always);
        a surcharge of 1 or more *dominates* the random weights, so boundary edges are effectively
        always chosen last and the bias is strong. Larger values mean a stronger preference to keep
        the region whole.

        Multiple region types: ``region_surcharge`` may contain several attributes (for example
        ``{"county": 0.5, "muni": 0.5}``). The surcharges are independent and *additive per edge*:
        an edge that crosses both a county boundary and a municipality boundary receives both
        surcharges. This lets you weight different kinds of region differently, but be aware that
        with several attributes the surcharges can stack, so keep the combined magnitudes in mind.

        Nodes with no region value (selectable via ``treat_unassigned_as_single_region``): an edge
        is surcharged whenever its endpoints do not share the same non-null attribute value. This
        always includes an edge between a region node and a region-less node (e.g. a node in no
        county). The one case you get to choose is an edge between *two* region-less nodes (both
        values ``None``), which decides how the "unassigned" territory for that attribute is treated:

        * **Region-less nodes individually splittable** (``treat_unassigned_as_single_region=False``,
          the default): edges among region-less nodes are also surcharged, so the unassigned area
          gets no "keep whole" bias and may be divided freely among districts. This is usually the
          right behavior when region-less nodes are scattered (water, unincorporated areas, etc.),
          where forcing them to stay together would make little sense.
        * **Unassigned area kept whole** (``treat_unassigned_as_single_region=True``): edges between
          two region-less nodes are left cheap (since they share the value ``None``), so all
          region-less nodes are treated like one additional region and biased to stay whole.

        The flag is applied per attribute, so for a given attribute its region-less nodes are
        treated consistently. It has no effect unless some nodes actually lack a value for a
        surcharged attribute.

    Args:
        graph (Graph): The input graph to build the spanning tree from.
        region_surcharge (Optional[Dict], optional): Dictionary mapping a node-attribute name to the
            numeric surcharge added to the random weight of edges that cross a boundary for that
            attribute. Defaults to None (no surcharge - an ordinary random spanning tree).
        treat_unassigned_as_single_region (bool, optional): How to treat edges between two nodes that
            both have no value for a surcharged attribute. When False (default), such edges are
            surcharged, so the region-less ("unassigned") area may be split freely. When True, such
            edges are not surcharged, so the region-less area is biased to be kept whole, like any
            other region. Has no effect when ``region_surcharge`` is empty or every node has a value.
        rng (Union[random.Random, int, None], optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Graph: The minimum spanning tree represented as a GerryChain Graph.

    Example:
        Draw a region-aware spanning tree of the bundled "Gerrymandria" example graph, biased to
        keep each county connected (and therefore split across as few districts as possible)::

            from gerrychain.examples import gerrymandria
            from gerrychain.tree import random_spanning_tree

            graph = gerrymandria()  # 8x8 graph with node attributes "county" and "water_dist"

            # A surcharge >= 1 dominates the [0, 1) random weights, strongly preferring to keep
            # whole counties together in the spanning tree. We also add a small surcharge for
            # water district boundaries to also indicate a preference to keep water together,
            # but the county surcharge is the main driver of the bias.
            tree = random_spanning_tree(graph, region_surcharge={"county": 2.0, "water_dist": 0.1})

        A spanning tree always has ``len(graph.nodes) - 1`` edges; with no ``region_surcharge`` you
        get an ordinary random spanning tree instead.
    """

    rng = make_rng(rng)

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
            graph.edge_data(edge_id)["random_weight"] = rng.random()
    else:
        for edge_id in graph.edge_indices:
            edge = graph.get_edge_from_edge_id(edge_id)
            weight = rng.random()

            for key, value in region_surcharge.items():
                node_id1 = edge[0]
                node_id2 = edge[1]
                node_id1_region = graph.node_data(node_id1)[key]
                node_id2_region = graph.node_data(node_id2)[key]
                if node_id1_region != node_id2_region:
                    # different regions, or exactly one endpoint is region-less: a boundary edge
                    weight += value
                elif node_id1_region is None and not treat_unassigned_as_single_region:
                    # both endpoints are region-less: surcharge unless keeping the unassigned
                    # area whole
                    weight += value

            graph.edge_data(edge_id)["random_weight"] = weight

    minimum_spanning_tree = graph.minimum_spanning_tree_from_edge_weight(
        edge_weight_attribute_name="random_weight"
    )
    return minimum_spanning_tree


def uniform_spanning_tree(
    graph: Graph,
    region_surcharge: dict = None,  # accepted for API compatibility, but unused
    *,
    rng: random.Random | int | None = None,
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
        graph (Graph): The graph from which to sample a spanning tree.
        region_surcharge (Optional[Dict], optional): Not used in this function.  It exists
            in the function signature so that all spanning tree functions will share the
            same signature.
        rng (Union[random.Random, int, None], optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Graph: A spanning tree of the graph chosen uniformly at random.
    """

    rng = make_rng(rng)

    if region_surcharge:
        raise ValueError("uniform_spanning_tree() region_surcharge paramter should be empty")

    # Pick a starting point at random
    root_id = rng.choice(list(graph.node_indices))

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
            parent_node_id[u] = rng.choice(list(graph.neighbors(u)))
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
