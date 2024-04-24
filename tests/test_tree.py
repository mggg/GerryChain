import functools

import networkx
import pytest

from gerrychain import MarkovChain
from gerrychain.constraints import contiguous, within_percent_of_ideal_population
from gerrychain.graph import Graph
from gerrychain.partition import Partition
from gerrychain.proposals import recom, reversible_recom
from gerrychain.tree import (
    bipartition_tree,
    random_spanning_tree,
    find_balanced_edge_cuts_contraction,
    find_balanced_edge_cuts_memoization,
    recursive_tree_part,
    recursive_seed_part,
    PopulatedGraph,
    uniform_spanning_tree,
    get_max_prime_factor_less_than,
    bipartition_tree_random,
)
from gerrychain.updaters import Tally, cut_edges
from functools import partial
import random

random.seed(2018)


@pytest.fixture
def graph_with_pop(three_by_three_grid):
    for node in three_by_three_grid:
        three_by_three_grid.nodes[node]["pop"] = 1
    return Graph.from_networkx(three_by_three_grid)


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
    return Graph.from_networkx(grid)


def test_bipartition_tree_returns_a_subset_of_nodes(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    result = bipartition_tree(graph_with_pop, "pop", ideal_pop, 0.25, 10)
    assert isinstance(result, frozenset)
    assert all(node in graph_with_pop.nodes for node in result)


def test_bipartition_tree_returns_within_epsilon_of_target_pop(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    epsilon = 0.25
    result = bipartition_tree(graph_with_pop, "pop", ideal_pop, epsilon, 10)

    part_pop = sum(graph_with_pop.nodes[node]["pop"] for node in result)
    assert abs(part_pop - ideal_pop) / ideal_pop < epsilon


def test_recursive_tree_part_returns_within_epsilon_of_target_pop(
    twelve_by_twelve_with_pop,
):
    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop.nodes[node]["pop"]
            for node in twelve_by_twelve_with_pop
        )
    ) / n_districts
    epsilon = 0.05
    result = recursive_tree_part(
        twelve_by_twelve_with_pop,
        range(n_districts),
        ideal_pop,
        "pop",
        epsilon,
    )
    partition = Partition(
        twelve_by_twelve_with_pop, result, updaters={"pop": Tally("pop")}
    )
    return all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )


def test_recursive_tree_part_returns_within_epsilon_of_target_pop_using_contraction(
    twelve_by_twelve_with_pop,
):
    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop.nodes[node]["pop"]
            for node in twelve_by_twelve_with_pop
        )
    ) / n_districts
    epsilon = 0.05
    result = recursive_tree_part(
        twelve_by_twelve_with_pop,
        range(n_districts),
        ideal_pop,
        "pop",
        epsilon,
        method=partial(
            bipartition_tree,
            max_attempts=10000,
            balance_edge_fn=find_balanced_edge_cuts_contraction,
        ),
    )
    partition = Partition(
        twelve_by_twelve_with_pop, result, updaters={"pop": Tally("pop")}
    )
    return all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )


def test_recursive_seed_part_returns_within_epsilon_of_target_pop(
    twelve_by_twelve_with_pop,
):
    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop.nodes[node]["pop"]
            for node in twelve_by_twelve_with_pop
        )
    ) / n_districts
    epsilon = 0.1
    result = recursive_seed_part(
        twelve_by_twelve_with_pop,
        range(n_districts),
        ideal_pop,
        "pop",
        epsilon,
        n=5,
        ceil=None,
    )
    partition = Partition(
        twelve_by_twelve_with_pop, result, updaters={"pop": Tally("pop")}
    )
    return all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )


def test_recursive_seed_part_returns_within_epsilon_of_target_pop_using_contraction(
    twelve_by_twelve_with_pop,
):
    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop.nodes[node]["pop"]
            for node in twelve_by_twelve_with_pop
        )
    ) / n_districts
    epsilon = 0.1
    result = recursive_seed_part(
        twelve_by_twelve_with_pop,
        range(n_districts),
        ideal_pop,
        "pop",
        epsilon,
        n=5,
        ceil=None,
        method=partial(
            bipartition_tree,
            max_attempts=10000,
            balance_edge_fn=find_balanced_edge_cuts_contraction,
        ),
    )
    partition = Partition(
        twelve_by_twelve_with_pop, result, updaters={"pop": Tally("pop")}
    )
    return all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )


def test_recursive_seed_part_uses_method(twelve_by_twelve_with_pop):
    calls = 0

    def dummy_method(graph, pop_col, pop_target, epsilon, node_repeats, one_sided_cut):
        nonlocal calls
        calls += 1
        return bipartition_tree(
            graph,
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            node_repeats=node_repeats,
            max_attempts=10000,
            one_sided_cut=one_sided_cut,
        )

    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop.nodes[node]["pop"]
            for node in twelve_by_twelve_with_pop
        )
    ) / n_districts
    epsilon = 0.1
    result = recursive_seed_part(
        twelve_by_twelve_with_pop,
        range(n_districts),
        ideal_pop,
        "pop",
        epsilon,
        n=5,
        ceil=None,
        method=dummy_method,
    )
    # Called at least once for each district besides the last one
    # (note that current implementation of recursive_seed_part calls method
    # EXACTLY once for each district besides the last one, but that is an
    # implementation detail)
    assert calls >= n_districts - 1


def test_recursive_seed_part_with_n_unspecified_within_epsilon(
    twelve_by_twelve_with_pop,
):
    n_districts = 6  # This should set n=3
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop.nodes[node]["pop"]
            for node in twelve_by_twelve_with_pop
        )
    ) / n_districts
    epsilon = 0.05
    result = recursive_seed_part(
        twelve_by_twelve_with_pop,
        range(n_districts),
        ideal_pop,
        "pop",
        epsilon,
        ceil=None,
    )
    partition = Partition(
        twelve_by_twelve_with_pop, result, updaters={"pop": Tally("pop")}
    )
    return all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )


def test_random_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop):
    tree = random_spanning_tree(graph_with_pop)
    assert networkx.is_tree(tree)


def test_uniform_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop):
    tree = uniform_spanning_tree(graph_with_pop)
    assert networkx.is_tree(tree)


def test_bipartition_tree_returns_a_tree(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    tree = Graph.from_networkx(
        networkx.Graph([(0, 1), (1, 2), (1, 4), (3, 4), (4, 5), (3, 6), (6, 7), (6, 8)])
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
    constraints = [contiguous]

    chain = MarkovChain(proposal, constraints, lambda x: True, partition_with_pop, 100)

    for state in chain:
        assert contiguous(state)


def test_reversible_recom_works_as_a_proposal(partition_with_pop):
    random.seed(2018)
    graph = partition_with_pop.graph
    ideal_pop = sum(graph.nodes[node]["pop"] for node in graph) / 2
    proposal = functools.partial(
        reversible_recom, pop_col="pop", pop_target=ideal_pop, epsilon=0.10, M=1
    )
    constraints = [within_percent_of_ideal_population(partition_with_pop, 0.25, "pop")]

    chain = MarkovChain(proposal, constraints, lambda x: True, partition_with_pop, 100)

    for state in chain:
        assert contiguous(state)


def test_find_balanced_cuts_contraction():
    tree = Graph.from_networkx(
        networkx.Graph([(0, 1), (1, 2), (1, 4), (3, 4), (4, 5), (3, 6), (6, 7), (6, 8)])
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


def test_no_balanced_cuts_contraction_when_one_side_okay():
    tree = Graph.from_networkx(networkx.Graph([(0, 1), (1, 2), (2, 3), (3, 4)]))

    populations = {0: 4, 1: 4, 2: 3, 3: 3, 4: 3}

    populated_tree = PopulatedGraph(
        graph=tree, populations=populations, ideal_pop=10, epsilon=0.1
    )

    cuts = find_balanced_edge_cuts_contraction(populated_tree, one_sided_cut=False)
    assert cuts == []


def test_find_balanced_cuts_memo():
    tree = Graph.from_networkx(
        networkx.Graph([(0, 1), (1, 2), (1, 4), (3, 4), (4, 5), (3, 6), (6, 7), (6, 8)])
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
    cuts = find_balanced_edge_cuts_memoization(populated_tree)
    edges = set(tuple(sorted(cut.edge)) for cut in cuts)
    assert edges == {(1, 4), (3, 4), (3, 6)}


def test_no_balanced_cuts_memo_when_one_side_okay():
    tree = Graph.from_networkx(networkx.Graph([(0, 1), (1, 2), (2, 3), (3, 4)]))

    populations = {0: 4, 1: 4, 2: 3, 3: 3, 4: 3}

    populated_tree = PopulatedGraph(
        graph=tree, populations=populations, ideal_pop=10, epsilon=0.1
    )

    cuts = find_balanced_edge_cuts_memoization(populated_tree)
    assert cuts == []


def test_prime_bound():
    assert (
        get_max_prime_factor_less_than(2024, 20) == 11
        and get_max_prime_factor_less_than(2024, 1) == None
        and get_max_prime_factor_less_than(2024, 2000) == 23
        and get_max_prime_factor_less_than(2024, -1) == None
    )


def test_bipartition_tree_random_returns_a_subset_of_nodes(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    result = bipartition_tree_random(graph_with_pop, "pop", ideal_pop, 0.25, 10)
    assert isinstance(result, frozenset)
    assert all(node in graph_with_pop.nodes for node in result)


def test_bipartition_tree_random_returns_within_epsilon_of_target_pop(graph_with_pop):
    ideal_pop = sum(graph_with_pop.nodes[node]["pop"] for node in graph_with_pop) / 2
    epsilon = 0.25
    result = bipartition_tree_random(graph_with_pop, "pop", ideal_pop, epsilon, 10)

    part_pop = sum(graph_with_pop.nodes[node]["pop"] for node in result)
    assert abs(part_pop - ideal_pop) / ideal_pop < epsilon
