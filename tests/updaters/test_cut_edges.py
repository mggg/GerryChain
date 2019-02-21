import functools

import pytest

from gerrychain import MarkovChain, Partition, proposals
from gerrychain.accept import always_accept
from gerrychain.constraints import (no_vanishing_districts,
                                    single_flip_contiguous)
from gerrychain.grid import Grid
from gerrychain.updaters import cut_edges, cut_edges_by_part

# This is copied and pasted, but should be done with some proper
# pytest configuration instead:


def edge_set_equal(set1, set2):
    return {(y, x) for x, y in set1} | set1 == {(y, x) for x, y in set2} | set2


def invalid_cut_edges(partition):
    invalid = [
        edge
        for edge in partition["cut_edges"]
        if partition.assignment[edge[0]] == partition.assignment[edge[1]]
    ]
    return invalid


def test_cut_edges_doesnt_duplicate_edges_with_different_order_of_nodes(
    three_by_three_grid
):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    partition = Partition(graph, assignment, {"cut_edges": cut_edges})
    # 112    111
    # 112 -> 121
    # 222    222
    flip = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flip)

    result = new_partition["cut_edges"]

    for edge in result:
        assert (edge[1], edge[0]) not in result


def test_cut_edges_can_handle_multiple_flips(three_by_three_grid):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    partition = Partition(graph, assignment, {"cut_edges": cut_edges})
    # 112    111
    # 112 -> 121
    # 222    222
    flip = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flip)

    result = new_partition["cut_edges"]

    naive_cut_edges = {
        tuple(sorted(edge)) for edge in graph.edges if new_partition.crosses_parts(edge)
    }
    assert result == naive_cut_edges


def test_cut_edges_by_part_doesnt_duplicate_edges_with_opposite_order_of_nodes(
    three_by_three_grid
):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {"cut_edges_by_part": cut_edges_by_part}
    partition = Partition(graph, assignment, updaters)
    # 112    111
    # 112 -> 121
    # 222    222
    flip = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flip)

    result = new_partition["cut_edges_by_part"]

    for part in result:
        for edge in result[part]:
            assert (edge[1], edge[0]) not in result


def test_cut_edges_by_part_gives_same_total_edges_as_naive_method(three_by_three_grid):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {"cut_edges_by_part": cut_edges_by_part}
    partition = Partition(graph, assignment, updaters)
    # 112    111
    # 112 -> 121
    # 222    222
    flip = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flip)

    result = new_partition["cut_edges_by_part"]
    naive_cut_edges = {
        tuple(sorted(edge)) for edge in graph.edges if new_partition.crosses_parts(edge)
    }

    assert naive_cut_edges == {
        tuple(sorted(edge)) for part in result for edge in result[part]
    }


def test_implementation_of_cut_edges_matches_naive_method(three_by_three_grid):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    partition = Partition(graph, assignment, {"cut_edges": cut_edges})

    flip = {4: 2}
    new_partition = Partition(parent=partition, flips=flip)
    result = cut_edges(new_partition)

    naive_cut_edges = {
        edge for edge in graph.edges if new_partition.crosses_parts(edge)
    }

    assert edge_set_equal(result, naive_cut_edges)


@pytest.mark.parametrize(
    "proposal,number_of_steps",
    [
        (proposals.propose_random_flip, 1000),
        (
            functools.partial(
                proposals.recom,
                pop_col="population",
                pop_target=25,
                epsilon=0.5,
                node_repeats=0,
            ),
            10,
        ),
    ],
)
def test_cut_edges_matches_naive_cut_edges_at_every_step(proposal, number_of_steps):
    partition = Grid((10, 10), with_diagonals=True)

    chain = MarkovChain(
        proposal,
        [single_flip_contiguous, no_vanishing_districts],
        always_accept,
        partition,
        number_of_steps,
    )

    for state in chain:
        naive_cut_edges = {
            edge for edge in state.graph.edges if state.crosses_parts(edge)
        }

        assert naive_cut_edges == state["cut_edges"]
