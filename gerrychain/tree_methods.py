import networkx as nx
from networkx.algorithms import tree

from .random import random


def predecessors(h, root):
    return {a: b for a, b in nx.bfs_predecessors(h, root)}


def random_spanning_tree(graph, pop_col):
    for edge in graph.edges:
        graph.edges[edge]["weight"] = random.random()

    edges = tree.maximum_spanning_edges(graph, algorithm="kruskal", data=False)
    spanning_tree = nx.Graph(edges)
    for node in graph:
        spanning_tree.nodes[node][pop_col] = graph.nodes[node][pop_col]
    return spanning_tree


def tree_part2(
    graph,
    pop_col,
    pop_target,
    epsilon,
    node_repeats,
    restarts=0,
    spanning_tree=None,
    choice=random.choice,
):
    """This function finds a balanced 2 partition of a graph by drawing a
    spanning tree and finding an edge to cut that leaves at most an epsilon
    imbalance between the populations of the parts. If a root fails, new roots
    are tried until node_repeats in which case a new tree is drawn.

    Builds up a connected subgraph with a connected complement whose population
    is ``epsilon * pop_target`` away from ``pop_target``.

    Returns a subset of nodes of ``graph`` (whose induced subgraph is connected).
    The other part of the partition is the complement of this subset.

    :param graph: The graph to partition
    :param pop_col: The node attribute holding the population of each node
    :param pop_target: The target population for the returned subset of nodes
    :param epsilon: The allowable deviation from  ``pop_target`` (as a percentage of
        ``pop_target``) for the subgraph's population
    :param node_repeats: A parameter for the algorithm: how many different choices
        of root to use before drawing a new spanning tree.
    :param restarts: Number of iterations (used when the algorithm chooses a new root)
    :param spanning_tree: The spanning tree for the algorithm to use (used when the
        algorithm chooses a new root and for testing)
    :param choice: :func:`random.choice`. Can be substituted for testing.
    """

    if spanning_tree is None:
        spanning_tree = random_spanning_tree(graph, pop_col)

    h = spanning_tree.copy()

    # this used to be greater than 2 but failed on small grids:(
    root = choice([x for x in spanning_tree.nodes if spanning_tree.degree(x) > 1])

    # BFS predecessors for iteratively contracting leaves
    pred = predecessors(h, root)

    # As we contract leaves, we keep track of which nodes merged together in
    # this dictionary:
    subsets = {x: {x} for x in graph}

    while len(h) > 1:
        leaves = [x for x in h if h.degree(x) == 1 and x != root]

        for leaf in leaves:
            if abs(h.nodes[leaf][pop_col] - pop_target) < epsilon * pop_target:
                return subsets[leaf]
            # Contract the leaf:
            parent = pred[leaf]
            h.nodes[parent][pop_col] += h.nodes[leaf][pop_col]
            subsets[parent] |= subsets[leaf]
            h.remove_node(leaf)

    if restarts < node_repeats:
        # Try again with new root, same tree
        return tree_part2(
            graph,
            pop_col,
            pop_target,
            epsilon,
            node_repeats,
            restarts + 1,
            spanning_tree,
        )
    else:
        # If restarts == node_repeats, start over completely with a new tree
        return tree_part2(graph, pop_col, pop_target, epsilon, node_repeats)
