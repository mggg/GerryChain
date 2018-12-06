import random

import networkx as nx

from proposals import propose_random_flip
from tree_methods import (get_spanning_tree_k, get_spanning_tree_u_w,
                          partition_spanning_tree_all,
                          partition_spanning_tree_single, propose_merge2_tree,
                          recursive_tree_full, tree_cycle_walk_all,
                          tree_cycle_walk_cut, tree_part2)

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


def propose_merge2_tree_partial(partition, pop_col, epsilon, node_repeats):
    """Partial ReCom walk for functools Partial
    merge_prop = partial(propose_merge2_tree_partial,pop_col="POP10",epsilon=.05,node_repeats=10)
    """
    edge = random.choice(tuple(partition["cut_edges"]))
    # print(edge)
    et = [partition.assignment[edge[0]], partition.assignment[edge[1]]]
    # print(et)
    sgn = []
    for n in partition.graph.nodes():
        if partition.assignment[n] in et:
            sgn.append(n)

    # print(len(sgn))
    sgraph = nx.subgraph(partition.graph, sgn)

    edd = {0: et[0], 1: et[1]}

    # print(edd)

    clusters = recursive_tree_part(
        partition,
        sgraph,
        2,
        pop_col=pop_col,
        epsilon=epsilon,
        node_repeats=node_repeats,
    )
    print("finished rtp")
    # print(len(clusters))
    flips = {}
    for val in clusters.keys():
        flips[val] = edd[clusters[val]]

    # print(len(flips))
    # print(partition.assignment)
    # print(flips)
    return flips


def recursive_tree_part(partition, graph, parts, pop_col, epsilon, node_repeats=20):
    """helper function for merge walk partitioning"""
    newlabels = {}
    pop_target = 0
    for node in graph.nodes():
        pop_target += partition.graph.nodes[node][pop_col]
    pop_target = pop_target / parts

    remaining_nodes = list(graph.nodes())
    for n in newlabels.keys():
        remaining_nodes.remove(n)
    sgraph = nx.subgraph(graph, remaining_nodes)

    for i in range(parts - 1):
        update = tree_part2(
            partition, sgraph, pop_col, pop_target, epsilon, node_repeats
        )  # should be part2

        for x in list(update[1]):
            newlabels[x] = i
        # update pop_target?
        remaining_nodes = list(graph.nodes())
        for n in newlabels.keys():
            remaining_nodes.remove(n)

        sgraph = nx.subgraph(graph, remaining_nodes)
        # print("Built District #", i)

    td = set(newlabels.keys())
    for nh in graph.nodes():
        if nh not in td:
            newlabels[nh] = parts - 1  # was +1 for initial testing
    return newlabels
