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
from .constraints import Validator
from typing import Callable, Dict, Iterator, Iterable, Union
from gerrychain.partition import Partition


def all_cut_edge_flips(partition: Partition) -> Iterator[Dict]:
    """
    Generate all possible flips of cut edges in a partition
    without any constraints.

    :param partition: The partition object.
    :type partition: Partition
    :returns: An iterator that yields dictionaries representing the flipped edges.
    :rtype: Iterator[Dict]
    """
    for edge, index in product(partition.cut_edges, (0, 1)):
        yield {edge[index]: partition.assignment.mapping[edge[1 - index]]}


def all_valid_states_one_flip_away(
    partition: Partition, constraints: Union[Iterable[Callable], Callable]
) -> Iterator[Partition]:
    """
    Generates all valid Partitions that differ from the given partition
    by one flip. These are the given partition's neighbors in the metagraph
    of partitions. (The metagraph of partitions is the set of partitions
    that is reachable from the given partition by a single flip under the
    prescribed constraints.)

    :param partition: The initial partition.
    :type partition: Partition
    :param constraints: Constraints to determine the validity of a partition.
                        It can be a single callable or an iterable of callables.
    :type constraints: Union[Iterable[Callable], Callable]
    :returns: An iterator that yields all valid partitions that differ from the
             given partition by one flip.
    :rtype: Iterator[Partition]
    """
    if callable(constraints):
        is_valid = constraints
    else:
        is_valid = Validator(constraints)

    for flip in all_cut_edge_flips(partition):
        next_state = partition.flip(flip)
        if is_valid(next_state):
            yield next_state


def all_valid_flips(
    partition: Partition, constraints: Union[Iterable[Callable], Callable]
) -> Iterator[Dict]:
    """
    Generate all valid flips for a given partition subject
    to the prescribed constraints.

    :param partition: The initial partition.
    :type partition: Partition
    :param constraints: The constraints to be satisfied. Can be a single
        constraint or an iterable of constraints.
    :type constraints: Union[Iterable[Callable], Callable]
    :returns: An iterator that yields dictionaries representing valid flips.
    :rtype: Iterator[Dict]
    """
    for state in all_valid_states_one_flip_away(partition, constraints):
        yield state.flips


def metagraph_degree(
    partition: Partition, constraints: Union[Iterable[Callable], Callable]
) -> int:
    """
    Calculate the degree of the node in the metagraph of the given partition.
    That is to say, compute how many possible valid states are reachable from
    the state given by partition in a single flip subject to the prescribed
    constraints.

    :param partition: The partition object representing the current state.
    :type partition: Partition
    :param constraints: The constraints to be applied to the partition.
                        It can be a single constraint or an iterable of constraints.
    :type constraints: Union[Iterable[Callable], Callable]
    :returns: The degree of the partition node in the metagraph.
    :rtype: int
    """
    return len(list(all_valid_states_one_flip_away(partition, constraints)))
