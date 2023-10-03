from itertools import product

from .constraints import Validator
from typing import Callable, Dict, Iterator, Iterable, Union

from gerrychain.partition import Partition


def all_cut_edge_flips(partition: Partition) -> Iterator[Dict]:
    for edge, index in product(partition.cut_edges, (0, 1)):
        yield {edge[index]: partition.assignment.mapping[edge[1 - index]]}


def all_valid_states_one_flip_away(
    partition: Partition,
    constraints: Union[Iterable[Callable], Callable]
) -> Iterator[Partition]:
    """Generates all valid Partitions that differ from the given partition
    by one flip. These are the given partition's neighbors in the metagraph
    of partitions.
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
    partition: Partition,
    constraints: Union[Iterable[Callable], Callable]
) -> Iterator[Dict]:
    for state in all_valid_states_one_flip_away(partition, constraints):
        yield state.flips


def metagraph_degree(
    partition: Partition,
    constraints: Union[Iterable[Callable], Callable]
) -> int:
    return len(list(all_valid_states_one_flip_away(partition, constraints)))
