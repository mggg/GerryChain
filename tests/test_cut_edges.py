import pytest

from rundmcmc.defaults import PA_partition, BasicChain
from rundmcmc.updaters import cut_edges, cut_edges_by_part
from rundmcmc.partition import Partition

# This is copied and pasted, but should be done with some proper
# pytest configuration instead:


def edge_set_equal(set1, set2):
    return {(y, x) for x, y in set1} | set1 == {(y, x) for x, y in set2} | set2


def invalid_cut_edges(partition):
    invalid = [edge for edge in partition['cut_edges']
               if partition.assignment[edge[0]] == partition.assignment[edge[1]]]
    return invalid


@pytest.mark.skip("We got rid of testData")
def test_cut_edges_only_returns_edges_that_are_actually_cut():
    partition = PA_partition()
    chain = BasicChain(partition, 100)
    for state in chain:
        assert invalid_cut_edges(state) == []


def test_cut_edges_doesnt_duplicate_edges_with_different_order_of_nodes(three_by_three_grid):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    partition = Partition(graph, assignment)
    # 112    111
    # 112 -> 121
    # 222    222
    flip = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flip)

    result = new_partition['cut_edges']

    for edge in result:
        assert (edge[1], edge[0]) not in result


def test_cut_edges_can_handle_multiple_flips(three_by_three_grid):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    partition = Partition(graph, assignment)
    # 112    111
    # 112 -> 121
    # 222    222
    flip = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flip)

    result = new_partition['cut_edges']

    naive_cut_edges = {tuple(sorted(edge)) for edge in graph.edges
                       if new_partition.crosses_parts(edge)}
    assert result == naive_cut_edges


def test_cut_edges_by_part_doesnt_duplicate_edges_with_opposite_order_of_nodes(three_by_three_grid):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {'cut_edges_by_part': cut_edges_by_part}
    partition = Partition(graph, assignment, updaters)
    # 112    111
    # 112 -> 121
    # 222    222
    flip = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flip)

    result = new_partition['cut_edges_by_part']

    for part in result:
        for edge in result[part]:
            assert (edge[1], edge[0]) not in result


def test_cut_edges_by_part_gives_same_total_edges_as_naive_method(three_by_three_grid):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {'cut_edges_by_part': cut_edges_by_part}
    partition = Partition(graph, assignment, updaters)
    # 112    111
    # 112 -> 121
    # 222    222
    flip = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flip)

    result = new_partition['cut_edges_by_part']
    naive_cut_edges = {tuple(sorted(edge)) for edge in graph.edges
                       if new_partition.crosses_parts(edge)}

    assert naive_cut_edges == {tuple(sorted(edge)) for part in result for edge in result[part]}


def test_implementation_of_cut_edges_matches_naive_method(three_by_three_grid):
    graph = three_by_three_grid
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    partition = Partition(graph, assignment)

    flip = {4: 2}
    new_partition = Partition(parent=partition, flips=flip)
    result = cut_edges(new_partition)

    naive_cut_edges = {edge for edge in graph.edges
                       if new_partition.crosses_parts(edge)}

    assert edge_set_equal(result, naive_cut_edges)
