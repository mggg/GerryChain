"""
This module defines proposal functions for use with MarkovChain.  A
proposal function is a function that takes a Partition as its only
parameter and returns a new Partition.

To make this explicit, the code defines a Protocol class with the
name ProposalFn which acts like a proposal function that takes one
parameter of a Partition and returns a Partition.

Because a ProposalFn must accept only a single Partition argument, any
additional information to be used by a ProposalFn needs to be bound
ahead of time.  Some proposal functions do not need additional
parameter values, but for those that do, the standard way to provide
those values is to create a "partial" function that binds all of
the additional parameter values, leaving only the Partition as the
sole remaining parameter.

For instance, the recom() function needs to know which bipartition function
to use, and so the appropriate bipartition function is bound in advance
using functools.partial().

Since using the paritial function or creating an appropriate closure can be
unintuitive, convenience functions are provided to perform this binding.
These convenience functions are of the form: build_xxx_proposal() where
"xxx" describes the semantics of proposal function.

"""

import random
from typing import Protocol

from ..partition import Partition


# Define a name for a Proposal function.
#
# This is just syntactic sugar, but it provides a way to
# document that an argument to a function should be one
# that takes a partition object as a param and returns
# a new partition.
#
class ProposalFn(Protocol):
    def __call__(self, x: Partition) -> Partition: ...


def propose_any_node_flip(partition: Partition) -> Partition:
    """Flip a random node (not necessarily on the boundary) to a random part.

    This function flip a random node (not necessarily on the boundary) to a random part. It returns
    a possible next `~gerrychain.Partition`.

    Args:
        partition (Partition): The current partition to propose a flip from.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """

    node = random.choice(tuple(partition.graph))
    newpart = random.choice(tuple(partition.parts))

    return partition.flip({node: newpart})


# Define a ProposalFn version to make purpose of the function clear
def build_propose_any_node_flip_proposal() -> ProposalFn:
    return propose_any_node_flip


def propose_flip_every_district(partition: Partition) -> Partition:
    """Proposes a random boundary flip for each district in the partition.

    This function proposes a random boundary flip for each district in the partition. It returns a
    possible next `~gerrychain.Partition`.

    Args:
        partition (Partition): The current partition to propose the flips from.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """
    flips = dict()

    for dist_edges in partition["cut_edges_by_part"].values():
        edge = random.choice(tuple(dist_edges))

        index = random.choice((0, 1))
        flipped_node, other_node = edge[index], edge[1 - index]
        flip = {flipped_node: partition.assignment.mapping[other_node]}

        flips.update(flip)

    return partition.flip(flips)


# Define a ProposalFn version to make purpose of the function clear
def build_propose_flip_every_district_proposal() -> ProposalFn:
    return propose_flip_every_district


def propose_chunk_flip(partition: Partition) -> Partition:
    """Chooses a random boundary node and proposes to flip it and all of its neighbors.

    This function chooses a random boundary node and proposes to flip it and all of its neighbors.
    It returns a possible next `~gerrychain.Partition`.

    Args:
        partition (Partition): The current partition to propose a flip from.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """
    flips = dict()

    edge = random.choice(tuple(partition["cut_edges"]))
    index = random.choice((0, 1))

    flipped_node = edge[index]

    valid_flips = [
        nbr
        for nbr in partition.graph.neighbors(flipped_node)
        if partition.assignment.mapping[nbr] != partition.assignment.mapping[flipped_node]
    ]

    for flipped_neighbor in valid_flips:
        flips.update({flipped_neighbor: partition.assignment.mapping[flipped_node]})

    return partition.flip(flips)


# Define a ProposalFn version to make purpose of the function clear
def build_propose_chunk_flip_proposal() -> ProposalFn:
    return propose_chunk_flip


def propose_random_flip(partition: Partition) -> Partition:
    """Proposes a random boundary flip from the partition.

    This function proposes a random boundary flip from the partition. It returns a possible next
    `~gerrychain.Partition`.

    Args:
        partition (Partition): The current partition to propose a flip from.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """
    if len(partition["cut_edges"]) == 0:
        return partition
    edge = random.choice(tuple(partition["cut_edges"]))
    index = random.choice((0, 1))
    flipped_node, other_node = edge[index], edge[1 - index]
    flip = {flipped_node: partition.assignment.mapping[other_node]}
    return partition.flip(flip)


# Define a ProposalFn version to make purpose of the function clear
def build_propose_random_flip_proposal() -> ProposalFn:
    return propose_random_flip


def slow_reversible_propose_bi(partition: Partition) -> Partition:
    """Proposes a random boundary flip from the partition in a reversible fashion.

    Selects a boundary node at random and uniformly picking one of its neighboring parts.
    For k-partitions this is not uniform since there might be multiple parts next to a single node.
    Temporary version until we make an updater for this set.

    Args:
        partition (Partition): The current partition to propose a flip from.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """

    b_nodes = {edge[0] for edge in partition["cut_edges"]}.union(
        {edge[1] for edge in partition["cut_edges"]}
    )

    flip = random.choice(list(b_nodes))
    neighbor_assignments = list(
        set(
            [partition.assignment.mapping[neighbor] for neighbor in partition.graph.neighbors(flip)]
        )
    )
    neighbor_assignments.remove(partition.assignment.mapping[flip])
    flips = {flip: random.choice(neighbor_assignments)}

    return partition.flip(flips)


flip = propose_random_flip


# Define a ProposalFn version to make purpose of the function clear
def build_slow_reversible_propose_bi_proposal() -> ProposalFn:
    return slow_reversible_propose_bi


def slow_reversible_propose(partition: Partition) -> Partition:
    """Proposes a random boundary flip from the partition in a reversible fashion

    Args:
        partition (Partition): The current partition to propose a flip from.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """

    b_nodes = {(x[0], partition.assignment.mapping[x[1]]) for x in partition["cut_edges"]}.union(
        {(x[1], partition.assignment.mapping[x[0]]) for x in partition["cut_edges"]}
    )

    flip = random.choice(list(b_nodes))
    return partition.flip({flip[0]: flip[1]})


# Define a ProposalFn version to make purpose of the function clear
def build_slow_reversible_propose_proposal() -> ProposalFn:
    return slow_reversible_propose
