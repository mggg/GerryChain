from ..random import random
from ..tree_methods import tree_part2


def recom(partition, pop_col, pop_target, epsilon, node_repeats):
    """ReCom proposal.

    Description from MGGG's 2018 Virginia House of Delegates report:
    At each step, we (uniformly) randomly select a pair of adjacent districts and
    merge all of their blocks in to a single unit. Then, we generate a spanning tree
    for the blocks of the merged unit with the Kruskal/Karger algorithm. Finally,
    we cut an edge of the tree at random, checking that this separates the region
    into two new districts that are population balanced.

    Example usage::

        from functools import partial
        from gerrychain import MarkovChain
        from gerrychain.proposals import recom

        # ...define constraints, accept, partition, total_steps here...

        # Ideal population:
        pop_target = sum(partition["population"].values()) / len(partition)

        proposal = partial(
            recom, pop_col="POP10", pop_target=pop_target, epsilon=.05, node_repeats=10
        )

        chain = MarkovChain(proposal, constraints, accept, partition, total_steps)

    """
    edge = random.choice(tuple(partition["cut_edges"]))
    parts_to_merge = (partition.assignment[edge[0]], partition.assignment[edge[1]])

    subgraph = partition.graph.subgraph(
        partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
    )

    flips = recursive_tree_part(
        subgraph,
        parts_to_merge,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
    )

    return partition.flip(flips)


def recursive_tree_part(graph, parts, pop_target, pop_col, epsilon, node_repeats=20):
    """helper function for merge walk partitioning.
    Uses :func:`~gerrychain.tree_methods.tree_part2` recursively to partition a tree into
    ``len(parts)`` parts of population ``pop_target`` (within ``epsilon``).

    :param graph: The graph
    :param parts: Iterable of part labels (like ``[0,1,2]`` or ``range(4)``
    :param pop_target: Target population for each part of the partition
    :param pop_col: Node attribute key holding population data
    :param epsilon: How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
        of the partition can be
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.tree_part2` to use.
    :return: New assignments for the nodes of ``graph``.
    :rtype: dict
    """
    flips = {}
    remaining_nodes = set(graph.nodes)

    for part in parts[:-1]:
        nodes = tree_part2(
            graph.subgraph(remaining_nodes), pop_col, pop_target, epsilon, node_repeats
        )

        for node in nodes:
            flips[node] = part
        # update pop_target?

        remaining_nodes -= nodes

    # All of the remaining nodes go in the last part
    for node in remaining_nodes:
        flips[node] = parts[-1]

    return flips
