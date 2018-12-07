import random

import networkx as nx

from proposals import propose_random_flip
from tree_methods import (
    get_spanning_tree_k,
    get_spanning_tree_u_w,
    partition_spanning_tree_all,
    partition_spanning_tree_single,
    propose_merge2_tree,
    recursive_tree_full,
    tree_cycle_walk_all,
    tree_cycle_walk_cut,
    tree_part2,
)

# Mixed proposals


def tree_mixed_proposal(partition, p):
    """ Do an ent step with probabiliity p
    otherwise single edge flip
    """
    if random.random() < p:
        flips = propose_bounce_single_cut(partition)
    else:
        flips = propose_random_flip(partition)

    return flips


def merge_mixed_proposal(partition, p):
    """ Do an ent step with probabiliity p
    otherwise single edge flip
    """

    if random.random() < p:
        flips = propose_merge2_tree(partition)
    else:
        flips = propose_random_flip(partition)

    return flips


#  Full-Tree Methods


def propose_allk_tree_k(partition, pop_col, epsilon, node_repeats):
    """Build a Karger tree and then partition it.
    """
    tree = nx.Graph()
    tree.add_edges_from(list(get_spanning_tree_k(partition.graph)))

    clusters = recursive_tree_full(
        partition, tree, len(partition.parts), pop_col, epsilon, node_repeats
    )

    return clusters


def propose_allk_tree_u(partition, pop_col, epsilon, node_repeats):
    """Build a unifrom tree and then partition it.
    """
    tree = nx.Graph()
    tree.add_edges_from(list(get_spanning_tree_u_w(partition.graph)))

    clusters = recursive_tree_full(
        partition, tree, len(partition.parts), pop_col, epsilon, node_repeats
    )

    return clusters


# These are different experiments for the ent walk


def propose_bounce_single_all(partition, pop_col, epsilon, node_repeats):
    """Ent walk that only adds enough cut edges
    and then adds an arbitrary graph edge
    """

    tree = partition_spanning_tree_single(partition)

    tree = tree_cycle_walk_all(partition, tree)

    clusters = recursive_tree_full(
        partition, tree, len(partition.parts), pop_col, epsilon, node_repeats
    )

    return clusters


def propose_bounce_single_cut(partition, pop_col, epsilon, node_repeats):
    """Ent walk that only adds enough cut edges
    and then adds an arbitrary cut edge
    """

    tree = partition_spanning_tree_single(partition)

    tree = tree_cycle_walk_cut(partition, tree)

    clusters = recursive_tree_full(
        partition, tree, len(partition.parts), pop_col, epsilon, node_repeats
    )

    return clusters


def propose_bounce_allcut_all(partition, pop_col, epsilon, node_repeats):
    """Ent walk that only adds all cut edges
    and then adds an arbitrary edge
    """

    tree = partition_spanning_tree_all(partition)

    tree = tree_cycle_walk_all(partition, tree)

    clusters = recursive_tree_full(
        partition, tree, len(partition.parts), pop_col, epsilon, node_repeats
    )

    return clusters


def propose_bounce_allcut_cut(partition, pop_col, epsilon, node_repeats):
    """Ent walk that only adds all cut edges
    and then adds an arbitrary cut edge
    """

    tree = partition_spanning_tree_all(partition)

    tree = tree_cycle_walk_cut(partition, tree)

    clusters = recursive_tree_full(
        partition, tree, len(partition.parts), pop_col, epsilon, node_repeats
    )

    return clusters


# Merge Proposal


def propose_merge2_tree_partial(partition, pop_col, pop_target, epsilon, node_repeats):
    """Partial ReCom walk for functools Partial
    merge_prop = partial(propose_merge2_tree_partial,pop_col="POP10",epsilon=.05,node_repeats=10)
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

    return flips


def recursive_tree_part(graph, parts, pop_target, pop_col, epsilon, node_repeats=20):
    """helper function for merge walk partitioning"""
    flips = {}
    remaining_nodes = set(graph.nodes)

    for part in parts[:-1]:
        nodes = tree_part2(
            graph.subgraph(remaining_nodes), pop_col, pop_target, epsilon, node_repeats
        )  # should be part2

        for node in nodes:
            flips[node] = part
        # update pop_target?

        remaining_nodes -= nodes

    # All remaining nodes go in the last part
    for node in remaining_nodes:
        flips[node] = parts[-1]

    return flips
