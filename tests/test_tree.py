import functools

import networkx
import pytest

from gerrychain import MarkovChain
from gerrychain.constraints import contiguous, within_percent_of_ideal_population
from gerrychain.partition import Partition
from gerrychain.proposals import recom
from gerrychain.tree import (
    bipartition_tree,
    random_spanning_tree,
    find_balanced_edge_cuts_contraction,
    recursive_tree_part,
    PopulatedGraph,
)
from gerrychain.updaters import Tally, cut_edges


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
        updaters={"pop": Tally("pop"), "cut_edges": cut_edges},
    )


@pytest.fixture
def twelve_by_twelve_with_pop():
    xy_grid = networkx.grid_graph([12, 12])
    nodes = {node: node[1] + 12 * node[0] for node in xy_grid}
    grid = networkx.relabel_nodes(xy_grid, nodes)
    for node in grid:
        grid.nodes[node]["pop"] = 1
    return grid


def test_bipartition_tree_returns_a_subset_of_nodes(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    result = bipartition_tree(graph_with_pop, "pop", ideal_pop, 0.25, 10)
    assert isinstance(result, set)
    assert all(node in graph_with_pop.nodes for node in result)


def test_bipartition_tree_returns_within_epsilon_of_target_pop(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    epsilon = 0.25
    result = bipartition_tree(graph_with_pop, "pop", ideal_pop, epsilon, 10)

    part_pop = sum(graph_with_pop.nodes[node]["pop"] for node in result)
    assert abs(part_pop - ideal_pop) / ideal_pop < epsilon


def test_recursive_tree_part_returns_within_epsilon_of_target_pop(twelve_by_twelve_with_pop):
    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (sum(twelve_by_twelve_with_pop.nodes[node]["pop"]
                     for node in twelve_by_twelve_with_pop)) / n_districts
    epsilon = 0.05
    result = recursive_tree_part(twelve_by_twelve_with_pop, range(n_districts),
                                 ideal_pop, "pop", epsilon)
    partition = Partition(twelve_by_twelve_with_pop, result,
                          updaters={"pop": Tally("pop")})
    return all(abs(part_pop - ideal_pop) / ideal_pop < epsilon
               for part_pop in partition['pop'].values())


def test_random_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop):
    tree = random_spanning_tree(graph_with_pop)
    assert networkx.is_tree(tree)


def test_bipartition_tree_returns_a_tree(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    tree = networkx.Graph(
        [(0, 1), (1, 2), (1, 4), (3, 4), (4, 5), (3, 6), (6, 7), (6, 8)]
    )
    for node in tree:
        tree.nodes[node]["pop"] = graph_with_pop.nodes[node]["pop"]

    result = bipartition_tree(
        graph_with_pop, "pop", ideal_pop, 0.25, 10, tree, lambda x: 4
    )

    assert networkx.is_tree(tree.subgraph(result))
    assert networkx.is_tree(
        tree.subgraph({node for node in tree if node not in result})
    )


def test_recom_works_as_a_proposal(partition_with_pop):
    graph = partition_with_pop.graph
    ideal_pop = sum(graph.nodes[node]["pop"] for node in graph) / 2
    proposal = functools.partial(
        recom, pop_col="pop", pop_target=ideal_pop, epsilon=0.25, node_repeats=5
    )
    constraints = [within_percent_of_ideal_population(partition_with_pop, 0.25, "pop")]

    chain = MarkovChain(proposal, constraints, lambda x: True, partition_with_pop, 100)

    for state in chain:
        assert contiguous(state)


def test_find_balanced_cuts_contraction():
    tree = networkx.Graph(
        [(0, 1), (1, 2), (1, 4), (3, 4), (4, 5), (3, 6), (6, 7), (6, 8)]
    )

    # 0 - 1 - 2
    #   ||
    # 3= 4 - 5
    # ||
    # 6- 7
    # |
    # 8

    populated_tree = PopulatedGraph(
        tree, {node: 1 for node in tree}, len(tree) / 2, 0.5
    )
    cuts = find_balanced_edge_cuts_contraction(populated_tree)
    edges = set(tuple(sorted(cut.edge)) for cut in cuts)
    assert edges == {(1, 4), (3, 4), (3, 6)}
