import random

# from typing import TypeVar
# Partition = TypeVar("Partition")
from ..partition import Partition


def propose_any_node_flip(partition: Partition) -> Partition:
    """
    Flip a random node (not necessarily on the boundary) to a random part

    :param partition: The current partition to propose a flip from.
    :type partition: Partition

    :returns: A possible next `~gerrychain.Partition`
    :rtype: Partition
    """

    node = random.choice(tuple(partition.graph))
    newpart = random.choice(tuple(partition.parts))

    return partition.flip({node: newpart})


def propose_flip_every_district(partition: Partition) -> Partition:
    """
    Proposes a random boundary flip for each district in the partition.

    :param partition: The current partition to propose the flips from.
    :type partition: Partition

    :returns: A possible next `~gerrychain.Partition`
    :rtype: Partition
    """
    flips = dict()

    for dist_edges in partition["cut_edges_by_part"].values():
        edge = random.choice(tuple(dist_edges))

        index = random.choice((0, 1))
        flipped_node, other_node = edge[index], edge[1 - index]
        flip = {flipped_node: partition.assignment.mapping[other_node]}

        flips.update(flip)

    return partition.flip(flips)


def propose_chunk_flip(partition: Partition) -> Partition:
    """
    Chooses a random boundary node and proposes to flip it and all of its neighbors

    :param partition: The current partition to propose a flip from.
    :type partition: Partition

    :returns: A possible next `~gerrychain.Partition`
    :rtype: Partition
    """
    flips = dict()

    edge = random.choice(tuple(partition["cut_edges"]))
    index = random.choice((0, 1))

    flipped_node = edge[index]

    valid_flips = [
        nbr
        for nbr in partition.graph.neighbors(flipped_node)
        if partition.assignment.mapping[nbr]
        != partition.assignment.mapping[flipped_node]
    ]

    for flipped_neighbor in valid_flips:
        flips.update({flipped_neighbor: partition.assignment.mapping[flipped_node]})

    return partition.flip(flips)


def propose_random_flip(partition: Partition) -> Partition:
    """
    Proposes a random boundary flip from the partition.

    :param partition: The current partition to propose a flip from.
    :type partition: Partition

    :returns: A possible next `~gerrychain.Partition`
    :rtype: Partition
    """
    if len(partition["cut_edges"]) == 0:
        return partition
    edge = random.choice(tuple(partition["cut_edges"]))
    index = random.choice((0, 1))
    flipped_node, other_node = edge[index], edge[1 - index]
    flip = {flipped_node: partition.assignment.mapping[other_node]}
    return partition.flip(flip)


def slow_reversible_propose_bi(partition: Partition) -> Partition:
    """
    Proposes a random boundary flip from the partition in a reversible fashion
    for bipartitions by selecting a boundary node at random and uniformly picking
    one of its neighboring parts. For k-partitions this is not uniform since there
    might be multiple parts next to a single node.

    Temporary version until we make an updater for this set.

    :param partition: The current partition to propose a flip from.
    :type partition: Partition

    :returns: A possible next `~gerrychain.Partition`
    :rtype: Partition
    """

    b_nodes = {x[0] for x in partition["cut_edges"]}.union(
        {x[1] for x in partition["cut_edges"]}
    )

    flip = random.choice(list(b_nodes))
    neighbor_assignments = list(
        set(
            [
                partition.assignment.mapping[neighbor]
                for neighbor in partition.graph.neighbors(flip)
            ]
        )
    )
    neighbor_assignments.remove(partition.assignment.mapping[flip])
    flips = {flip: random.choice(neighbor_assignments)}

    return partition.flip(flips)


flip = propose_random_flip


def slow_reversible_propose(partition: Partition) -> Partition:
    """
    Proposes a random boundary flip from the partition in a reversible fasion
    by selecting uniformly from the (node, flip) pairs.

    Temporary version until we make an updater for this set.

    :param partition: The current partition to propose a flip from.
    :type partition: Partition

    :returns: A possible next `~gerrychain.Partition`
    :rtype: Partition
    """

    b_nodes = {
        (x[0], partition.assignment.mapping[x[1]]) for x in partition["cut_edges"]
    }.union(
        {(x[1], partition.assignment.mapping[x[0]]) for x in partition["cut_edges"]}
    )

    flip = random.choice(list(b_nodes))
    return partition.flip({flip[0]: flip[1]})
