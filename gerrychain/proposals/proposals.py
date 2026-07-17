"""
This module defines proposal functions for use with MarkovChain.

A ProposalFn is a function that takes a Partition and RNG and returns a new Partition. It is used
by the MarkovChain to generate the next Partition at each step of the chain.

Additional proposal information is bound ahead of time. This is often done by partially applying
the proposal function with functools.partial, or by using a helper function that returns a closure
capturing the additional parameters.

For instance, the recom() function needs to know which bipartition function to use, and so the
appropriate bipartition function is bound in advance through one of the aformentioned methods and
the returned ProposalFn will have the expected signature.

Since using the paritial function or creating an appropriate closure can be
unintuitive, convenience functions are often provided to perform this binding.
"""

# frm: TODO: Documentation: Peter - are you OK with the comments above?

import random
from typing import Protocol

from .._rng import make_rng
from ..partition import Partition


# Define a name for a Proposal function.
#
# This is just syntactic sugar, but it provides a way to
# document that an argument to a function should be one
# that takes a partition object as a param and returns
# a new partition.
#
class ProposalFn(Protocol):
    """Propose a new partition, called as ``proposal_fn(partition, rng=rng)``."""

    def __call__(self, partition: Partition, /, *, rng: random.Random) -> Partition: ...


def propose_any_node_flip(
    partition: Partition, *, rng: random.Random | int | None = None
) -> Partition:
    """Flip a random node (not necessarily on the boundary) to a random part.

    This function flip a random node (not necessarily on the boundary) to a random part. It returns
    a possible next `~gerrychain.Partition`.

    Args:
        partition (Partition): The current partition to propose a flip from.
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """

    rng = make_rng(rng)
    node = rng.choice(tuple(partition.graph))
    newpart = rng.choice(tuple(partition.parts))

    return partition.flip({node: newpart})


# Define a ProposalFn version to make purpose of the function clear
def build_any_node_flip_proposal_fn() -> ProposalFn:
    return propose_any_node_flip


def propose_flip_every_district(
    partition: Partition, *, rng: random.Random | int | None = None
) -> Partition:
    """Proposes a random boundary flip for each district in the partition.

    This function proposes a random boundary flip for each district in the partition. It returns a
    possible next `~gerrychain.Partition`.

    Args:
        partition (Partition): The current partition to propose the flips from.
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """
    flips = dict()
    rng = make_rng(rng)

    for dist_edges in partition["cut_edges_by_part"].values():
        edge = rng.choice(tuple(dist_edges))

        index = rng.choice((0, 1))
        flipped_node, other_node = edge[index], edge[1 - index]
        flip = {flipped_node: partition.assignment.mapping[other_node]}

        flips.update(flip)

    return partition.flip(flips)


# Define a ProposalFn version to make purpose of the function clear
def build_flip_every_district_proposal_fn() -> ProposalFn:
    return propose_flip_every_district


def propose_chunk_flip(
    partition: Partition, *, rng: random.Random | int | None = None
) -> Partition:
    """Chooses a random boundary node and proposes to flip it and all of its neighbors.

    This function chooses a random boundary node and proposes to flip it and all of its neighbors.
    It returns a possible next `~gerrychain.Partition`.

    Args:
        partition (Partition): The current partition to propose a flip from.
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """
    flips = dict()
    rng = make_rng(rng)

    edge = rng.choice(tuple(partition["cut_edges"]))
    index = rng.choice((0, 1))

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
def build_chunk_flip_proposal_fn() -> ProposalFn:
    return propose_chunk_flip


def propose_random_flip(
    partition: Partition, *, rng: random.Random | int | None = None
) -> Partition:
    """Proposes a random boundary flip from the partition.

    This function proposes a random boundary flip from the partition. It returns a possible next
    `~gerrychain.Partition`.

    Args:
        partition (Partition): The current partition to propose a flip from.
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """
    if len(partition["cut_edges"]) == 0:
        return partition
    rng = make_rng(rng)
    edge = rng.choice(tuple(partition["cut_edges"]))
    index = rng.choice((0, 1))
    flipped_node, other_node = edge[index], edge[1 - index]
    flip = {flipped_node: partition.assignment.mapping[other_node]}
    return partition.flip(flip)


# Define a ProposalFn version to make purpose of the function clear
def build_random_flip_proposal_fn() -> ProposalFn:
    return propose_random_flip


def slow_reversible_propose_bi(
    partition: Partition, *, rng: random.Random | int | None = None
) -> Partition:
    """Proposes a random boundary flip from the partition in a reversible fashion.

    Selects a boundary node at random and uniformly picking one of its neighboring parts.
    For k-partitions this is not uniform since there might be multiple parts next to a single node.
    Temporary version until we make an updater for this set.

    Args:
        partition (Partition): The current partition to propose a flip from.
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """

    rng = make_rng(rng)
    part_order = {part: index for index, part in enumerate(partition.parts)}
    b_nodes = {edge[0] for edge in partition["cut_edges"]}.union(
        {edge[1] for edge in partition["cut_edges"]}
    )

    flip = rng.choice(list(b_nodes))
    neighbor_assignments = sorted(
        {partition.assignment.mapping[neighbor] for neighbor in partition.graph.neighbors(flip)},
        key=part_order.__getitem__,
    )
    neighbor_assignments.remove(partition.assignment.mapping[flip])
    flips = {flip: rng.choice(neighbor_assignments)}

    return partition.flip(flips)


flip = propose_random_flip


# Define a ProposalFn version to make purpose of the function clear
def build_slow_reversible_bi_proposal_fn() -> ProposalFn:
    return slow_reversible_propose_bi


def slow_reversible_propose(
    partition: Partition, *, rng: random.Random | int | None = None
) -> Partition:
    """Proposes a random boundary flip from the partition in a reversible fashion

    Args:
        partition (Partition): The current partition to propose a flip from.
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Partition: A possible next `~gerrychain.Partition`
    """

    rng = make_rng(rng)
    part_order = {part: index for index, part in enumerate(partition.parts)}
    b_nodes = {(x[0], partition.assignment.mapping[x[1]]) for x in partition["cut_edges"]}.union(
        {(x[1], partition.assignment.mapping[x[0]]) for x in partition["cut_edges"]}
    )

    flip = rng.choice(sorted(b_nodes, key=lambda item: (item[0], part_order[item[1]])))
    return partition.flip({flip[0]: flip[1]})


# Define a ProposalFn version to make purpose of the function clear
def build_slow_reversible_proposal_fn() -> ProposalFn:
    return slow_reversible_propose
