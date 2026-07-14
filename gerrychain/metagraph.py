"""
This module provides the main tools for interacting with the metagraph of partitions.
The metagraph of partitions is the set of partitions that are reachable from the
current partition by a single flip.

Dependencies:

- itertools: Used for product() function.
- typing: Used for type hints.

Last Updated: 11 Jan 2024
"""

from itertools import product
from collections.abc import Hashable, Iterable, Iterator
from typing import cast

from gerrychain.partition import Partition

from .constraints import Validator, ConstraintFn


def all_cut_edge_flips(partition: Partition) -> Iterator[dict[Hashable, Hashable]]:
    """Generate all possible flips of cut edges in a partition without any constraints.

    This routine finds all edges on the boundary of districts - those that are "cut edges" where
    one node is in one district and the other node is in another district. These are all of the
    places where you could move the boundary between districts by moving a single node.

    Args:
        partition (Partition): The partition object.

    Returns:
        Iterator[dict[Hashable, Hashable]]: An iterator that yields dictionaries representing
            the flipped edges.
    """

    for edge, index in product(partition["cut_edges"], (0, 1)):
        yield {edge[index]: partition.assignment.mapping[edge[1 - index]]}


def all_valid_states_one_flip_away(
    partition: Partition, constraints: ConstraintFn | Iterable[ConstraintFn] | Validator
) -> Iterator[Partition]:
    """Generates all valid Partitions that differ from the given partition by one flip.

    These are the given partition's neighbors in the metagraph of partitions. (The metagraph of
    partitions is the set of partitions that is reachable from the given partition by a single flip
    under the prescribed constraints.)

    Args:
        partition (Partition): The initial partition.
        constraints (ConstraintFn | Iterable[ConstraintFn] | Validator): Constraints determining
            whether a partition is valid.

    Returns:
        Iterator[Partition]: An iterator that yields all valid partitions that differ from the
            given partition by one flip.
    """
    if isinstance(constraints, Validator):
        validator = constraints
    elif callable(constraints):
        validator = cast(ConstraintFn, constraints)
    else:
        validator = Validator(constraints)

    for flip in all_cut_edge_flips(partition):
        next_state = partition.flip(flip)
        if validator(next_state):
            yield next_state


def all_valid_flips(
    partition: Partition, constraints: ConstraintFn | Iterable[ConstraintFn] | Validator
) -> Iterator[dict[Hashable, Hashable]]:
    """Generate all valid flips for a given partition subject to the prescribed constraints.

    This function generates all valid flips for a given partition subject to the prescribed
    constraints. It returns an iterator that yields dictionaries representing valid flips.

    Args:
        partition (Partition): The initial partition.
        constraints (ConstraintFn | Iterable[ConstraintFn] | Validator): Constraints determining
            whether a partition is valid.

    Returns:
        Iterator[dict[Hashable, Hashable]]: An iterator that yields dictionaries representing
            valid flips.
    """
    for state in all_valid_states_one_flip_away(partition, constraints):
        assert state.flips is not None
        yield state.flips


def metagraph_degree(
    partition: Partition, constraints: ConstraintFn | Iterable[ConstraintFn] | Validator
) -> int:
    """Calculate the degree of the node in the metagraph of the given partition.

    That is to say, compute how many possible valid states are reachable from the state given by
    partition in a single flip subject to the prescribed constraints.

    Args:
        partition (Partition): The partition object representing the current state.
        constraints (ConstraintFn | Iterable[ConstraintFn] | Validator): Constraints determining
            whether a partition is valid.

    Returns:
        int: The degree of the partition node in the metagraph.
    """
    return len(list(all_valid_states_one_flip_away(partition, constraints)))
