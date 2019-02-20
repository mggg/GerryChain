from itertools import product

from .constraints import Validator


def all_cut_edge_flips(partition):
    for edge, index in product(partition.cut_edges, (0, 1)):
        yield {edge[index]: partition.assignment[edge[1 - index]]}


def all_valid_states_one_flip_away(partition, constraints):
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


def all_valid_flips(partition, constraints):
    for state in all_valid_states_one_flip_away(partition, constraints):
        yield state.flips


def metagraph_degree(partition, constraints):
    return len(list(all_valid_states_one_flip_away(partition, constraints)))
