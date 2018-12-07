import networkx
import pytest

from gerrychain.partition import Partition
from gerrychain.tree_methods import random_spanning_tree, tree_part2
from gerrychain.updaters import Tally


@pytest.fixture
def graph_with_pop(three_by_three_grid):
    for node in three_by_three_grid:
        three_by_three_grid.nodes[node]["pop"] = 1
    return three_by_three_grid


@pytest.fixture
def partition_with_pop(graph_with_pop):
    return Partition(
        graph_with_pop,
        {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 1, 7: 1, 8: 1},
        updaters={"pop": Tally("pop")},
    )


def test_tree_part2_returns_a_subset_of_nodes(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    result = tree_part2(graph_with_pop, "pop", ideal_pop, 0.25, 10)
    assert isinstance(result, set)
    assert all(node in graph_with_pop.nodes for node in result)


def test_tree_part2_returns_within_epsilon_of_target_pop(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    epsilon = 0.25
    result = tree_part2(graph_with_pop, "pop", ideal_pop, epsilon, 10)

    part_pop = sum(graph_with_pop.nodes[node]["pop"] for node in result)
    assert abs(part_pop - ideal_pop) / ideal_pop < epsilon


def test_random_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop):
    tree = random_spanning_tree(graph_with_pop, "pop")
    assert networkx.is_tree(tree)
    for node in tree:
        assert tree.nodes[node]["pop"] == graph_with_pop.nodes[node]["pop"]


def test_tree_part2_returns_a_tree(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    tree = networkx.Graph(
        [(0, 1), (1, 2), (1, 4), (3, 4), (4, 5), (3, 6), (6, 7), (6, 8)]
    )
    for node in tree:
        tree.nodes[node]["pop"] = graph_with_pop.nodes[node]["pop"]

    result = tree_part2(
        graph_with_pop, "pop", ideal_pop, 0.25, 10, 0, tree, lambda x: 4
    )

    assert networkx.is_tree(tree.subgraph(result))
    assert networkx.is_tree(
        tree.subgraph({node for node in tree if node not in result})
    )
