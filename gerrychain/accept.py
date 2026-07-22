"""
This module provides the main acceptance function used in ReCom Markov chains.

Last Updated: 11 Jan 2024
"""

import random
from typing import Protocol

from gerrychain.partition import Partition


class AcceptanceFn(Protocol):
    """Accept or reject a proposal, called as ``acceptance_fn(partition, rng=rng)``."""

    def __call__(self, partition: Partition, /, *, rng: random.Random) -> bool: ...


def always_accept(partition: Partition, *, rng: random.Random) -> bool:
    """Always accepts the a proposed next state.

    Args:
        partition (Partition): The current partition to accept a flip from.
        rng (random.Random): The chain's random number generator. Unused by this function.

    Returns:
        bool: True
    """
    return True


def cut_edge_accept(partition: Partition, *, rng: random.Random) -> bool:
    """Always accepts the flip if the number of cut_edges decreases Otherwise, uses the Metropolis.

    This function always accepts the flip if the number of cut_edges decreases. Otherwise, uses the
    Metropolis criterion to determine whether to accept the flip. The Metropolis criterion accepts
    the flip with probability min(1, old_cut_edges/new_cut_edges) where old_cut_edges is the number
    of cut edges in the parent partition and new_cut_edges is the number of cut edges in the
    proposed partition.

    The idea is to use the acceptance function to drive the
    algorithm towards districts that are more compact. In some sense, the
    number of cut edges in a districting plan is a measure of compactness,
    so always accepting when the number of cut edges decreases improves
    the compactness score.

    However, sometimes it is not possible to improve the score any further
    in a neighborhood of your current state, so you allow the chain to get
    unstuck by accepting something "worse" with a probability proportional
    to how much worse it has gotten.

    This is more useful when running "flip" chains rather than ReCom chains
    because flip chains have a tendency to produce districts that are not very compact.

    Args:
        partition (Partition): The current partition to accept a flip from.
        rng (random.Random): The chain's random number generator.

    Returns:
        bool: True if accepted, False to remain in place
    """

    if partition.parent is None:
        return True

    # Determine if the current partition is more compact than its parent
    #
    parent_partition_compactness_proxy = len(partition.parent["cut_edges"])
    current_partition_compactness_proxy = len(partition["cut_edges"])
    current_is_more_compact_than_parent = (
        current_partition_compactness_proxy < parent_partition_compactness_proxy
    )

    # If the current partition is more compact than its parent then return True
    if current_is_more_compact_than_parent:
        return True

    # The current partition is NOT more compact than its parent, so we want
    # sometimes accept and sometimes reject it - we want to reject it because
    # compactness is good, but we need to make sure that the algorithm does
    # not get stuck, so we sometimes accept it.
    #
    # If the parent is much more compact than the current partition, then we
    # are more aggressive in rejecting the current partition.  We do this
    # by setting a bound based on the ratio of compactness and then comparing
    # that bound against a random number - the smaller the bound the greater
    # likelihood that the current partition will be rejected.
    #
    bound = parent_partition_compactness_proxy / current_partition_compactness_proxy
    return rng.random() < bound
