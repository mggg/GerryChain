import functools

import networkx
import rustworkx
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

#
# This code is complicated by the need to test both NX-based
# and RX-based Graph objects.  
#
# The pattern is to define the test logic in a routine that
# will be run with both NX-based and RX-based Graph objects
# and to then have the actual test case call that logic.
# This buries the asserts down a level, which means that
# figuring out what went wrong if a test fails will be
# slightly more challenging, but it keeps the logic for
# testing both NX-based and RX-based Graph objects clean.
#

@pytest.fixture
def graph_with_pop_nx(three_by_three_grid):
    # NX-based Graph object
    for node in three_by_three_grid:
        three_by_three_grid.node_data(node)["pop"] = 1
    return three_by_three_grid

@pytest.fixture
def graph_with_pop_rx(graph_with_pop_nx):
    # RX-based Graph object (same data as NX-based version)
    graph_rx = graph_with_pop_nx.convert_from_nx_to_rx()
    return graph_rx

@pytest.fixture
def partition_with_pop(graph_with_pop_nx):
    # No need for an RX-based Graph here because creating the 
    # Partition object converts the graph to be RX-based if
    # it is not already RX-based 
    #
    return Partition(
        graph_with_pop_nx,
        {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 1, 7: 1, 8: 1},
        updaters={"pop": Tally("pop"), "cut_edges": cut_edges},
    )

@pytest.fixture
def twelve_by_twelve_with_pop_nx():
    # NX-based Graph object 

    xy_grid = networkx.grid_graph([12, 12])

    # Relabel nodes with integers rather than tuples.  Node
    # in cartesian coordinate (x,y) will be relabeled with
    # the integer = x*12 + y , which just numbers nodes
    # sequentially from 0 by row...
    #
    nodes = {node: node[1] + 12 * node[0] for node in xy_grid}
    grid = networkx.relabel_nodes(xy_grid, nodes)

    for node in grid:
        grid.nodes[node]["pop"] = 1
    return Graph.from_networkx(grid)

@pytest.fixture
def twelve_by_twelve_with_pop_rx(twelve_by_twelve_with_pop_nx):
    # RX-based Graph object (same data as NX-based version)
    graph_rx = twelve_by_twelve_with_pop_nx.convert_from_nx_to_rx()
    return graph_rx

# ---------------------------------------------------------------------

def do_test_bipartition_tree_random_returns_a_subset_of_nodes(graph):
    ideal_pop = sum(graph.node_data(node)["pop"] for node in graph) / 2
    result = bipartition_tree_random(graph, "pop", ideal_pop, 0.25, 10)
    assert isinstance(result, frozenset)
    assert all(node in graph.nodes for node in result)

def test_bipartition_tree_random_returns_a_subset_of_nodes(graph_with_pop_nx, graph_with_pop_rx):
    # Test both NX-based and RX-based Graph objects
    do_test_bipartition_tree_random_returns_a_subset_of_nodes(graph_with_pop_nx)
    do_test_bipartition_tree_random_returns_a_subset_of_nodes(graph_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_bipartition_tree_random_returns_within_epsilon_of_target_pop(graph):
    ideal_pop = sum(graph.node_data(node)["pop"] for node in graph) / 2
    epsilon = 0.25
    result = bipartition_tree_random(graph, "pop", ideal_pop, epsilon, 10)

    part_pop = sum(graph.node_data(node)["pop"] for node in result)
    assert abs(part_pop - ideal_pop) / ideal_pop < epsilon

def test_bipartition_tree_random_returns_within_epsilon_of_target_pop(
      graph_with_pop_nx, 
      graph_with_pop_rx
):
    # Test both NX-based and RX-based Graph objects
    do_test_bipartition_tree_random_returns_within_epsilon_of_target_pop(graph_with_pop_nx)
    do_test_bipartition_tree_random_returns_within_epsilon_of_target_pop(graph_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_bipartition_tree_returns_a_subset_of_nodes(graph):
    ideal_pop = sum(graph.node_data(node)["pop"] for node in graph) / 2
    result = bipartition_tree(graph, "pop", ideal_pop, 0.25, 10)
    assert isinstance(result, frozenset)
    assert all(node in graph.nodes for node in result)

def test_bipartition_tree_returns_a_subset_of_nodes(graph_with_pop_nx, graph_with_pop_rx):
    # Test both NX-based and RX-based Graph objects
    do_test_bipartition_tree_returns_a_subset_of_nodes(graph_with_pop_nx)
    do_test_bipartition_tree_returns_a_subset_of_nodes(graph_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_bipartition_tree_returns_within_epsilon_of_target_pop(graph):
    ideal_pop = sum(graph.node_data(node)["pop"] for node in graph) / 2
    epsilon = 0.25
    result = bipartition_tree(graph, "pop", ideal_pop, epsilon, 10)

    part_pop = sum(graph.node_data(node)["pop"] for node in result)
    assert abs(part_pop - ideal_pop) / ideal_pop < epsilon

def test_bipartition_tree_returns_within_epsilon_of_target_pop(graph_with_pop_nx, graph_with_pop_rx):
    # Test both NX-based and RX-based Graph objects
    do_test_bipartition_tree_returns_within_epsilon_of_target_pop(graph_with_pop_nx)
    do_test_bipartition_tree_returns_within_epsilon_of_target_pop(graph_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_recursive_tree_part_returns_within_epsilon_of_target_pop(twelve_by_twelve_with_pop_graph):
    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop_graph.node_data(node)["pop"]
            for node in twelve_by_twelve_with_pop_graph
        )
    ) / n_districts
    epsilon = 0.05
    result = recursive_tree_part(
        twelve_by_twelve_with_pop_graph,
        range(n_districts),
        ideal_pop,
        "pop",
        epsilon,
    )
    partition = Partition(
        twelve_by_twelve_with_pop_graph, result, updaters={"pop": Tally("pop")}
    )
    # frm: Original Code:
    #
    #    return all(
    #        abs(part_pop - ideal_pop) / ideal_pop < epsilon
    #        for part_pop in partition["pop"].values()
    #    )
    assert all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )

def test_recursive_tree_part_returns_within_epsilon_of_target_pop(
    twelve_by_twelve_with_pop_nx,
    twelve_by_twelve_with_pop_rx
):
    # Test both NX-based and RX-based Graph objects
    do_test_recursive_tree_part_returns_within_epsilon_of_target_pop(twelve_by_twelve_with_pop_nx)
    do_test_recursive_tree_part_returns_within_epsilon_of_target_pop(twelve_by_twelve_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_recursive_tree_part_returns_within_epsilon_of_target_pop_using_contraction(
    twelve_by_twelve_with_pop_graph,
):
    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop_graph.node_data(node)["pop"]
            for node in twelve_by_twelve_with_pop_graph
        )
    ) / n_districts
    epsilon = 0.05
    result = recursive_tree_part(
        twelve_by_twelve_with_pop_graph,
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
        twelve_by_twelve_with_pop_graph, result, updaters={"pop": Tally("pop")}
    )
    # frm: Original Code:
    #
    #    return all(
    #        abs(part_pop - ideal_pop) / ideal_pop < epsilon
    #        for part_pop in partition["pop"].values()
    #    )
    #
    assert all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )

def test_recursive_tree_part_returns_within_epsilon_of_target_pop_using_contraction(
    twelve_by_twelve_with_pop_nx,
    twelve_by_twelve_with_pop_rx
):
    # Test both NX-based and RX-based Graph objects
    do_test_recursive_tree_part_returns_within_epsilon_of_target_pop_using_contraction(
      twelve_by_twelve_with_pop_nx
    )
    do_test_recursive_tree_part_returns_within_epsilon_of_target_pop_using_contraction(
      twelve_by_twelve_with_pop_rx
    )

# ---------------------------------------------------------------------

def do_test_recursive_seed_part_returns_within_epsilon_of_target_pop(
    twelve_by_twelve_with_pop_graph,
):
    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop_graph.node_data(node)["pop"]
            for node in twelve_by_twelve_with_pop_graph
        )
    ) / n_districts
    epsilon = 0.1
    result = recursive_seed_part(
        twelve_by_twelve_with_pop_graph,
        range(n_districts),
        ideal_pop,
        "pop",
        epsilon,
        n=5,
        ceil=None,
    )
    partition = Partition(
        twelve_by_twelve_with_pop_graph, result, updaters={"pop": Tally("pop")}
    )
    # frm: Original Code:
    #
    #    return all(
    #        abs(part_pop - ideal_pop) / ideal_pop < epsilon
    #        for part_pop in partition["pop"].values()
    #    )
    assert all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )

def test_recursive_seed_part_returns_within_epsilon_of_target_pop(
    twelve_by_twelve_with_pop_nx,
    twelve_by_twelve_with_pop_rx
):
    # Test both NX-based and RX-based Graph objects
    do_test_recursive_seed_part_returns_within_epsilon_of_target_pop(twelve_by_twelve_with_pop_nx)
    do_test_recursive_seed_part_returns_within_epsilon_of_target_pop(twelve_by_twelve_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_recursive_seed_part_returns_within_epsilon_of_target_pop_using_contraction(
    twelve_by_twelve_with_pop_graph,
):
    n_districts = 7  # 144/7 ≈ 20.5 nodes/subgraph (1 person/node)
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop_graph.node_data(node)["pop"]
            for node in twelve_by_twelve_with_pop_graph
        )
    ) / n_districts
    epsilon = 0.1
    result = recursive_seed_part(
        twelve_by_twelve_with_pop_graph,
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
        twelve_by_twelve_with_pop_graph, result, updaters={"pop": Tally("pop")}
    )
    # frm: Original Code:
    #
    #    return all(
    #        abs(part_pop - ideal_pop) / ideal_pop < epsilon
    #        for part_pop in partition["pop"].values()
    #    )
    assert all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )

def test_recursive_seed_part_returns_within_epsilon_of_target_pop_using_contraction(
    twelve_by_twelve_with_pop_nx,
    twelve_by_twelve_with_pop_rx
):
    # Test both NX-based and RX-based Graph objects
    do_test_recursive_seed_part_returns_within_epsilon_of_target_pop_using_contraction(
      twelve_by_twelve_with_pop_nx
    )
    do_test_recursive_seed_part_returns_within_epsilon_of_target_pop_using_contraction(
      twelve_by_twelve_with_pop_rx
    )

# ---------------------------------------------------------------------

def do_test_recursive_seed_part_uses_method(twelve_by_twelve_with_pop_graph):
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
            twelve_by_twelve_with_pop_graph.node_data(node)["pop"]
            for node in twelve_by_twelve_with_pop_graph
        )
    ) / n_districts
    epsilon = 0.1
    result = recursive_seed_part(
        twelve_by_twelve_with_pop_graph,
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

def test_recursive_seed_part_uses_method(twelve_by_twelve_with_pop_nx, twelve_by_twelve_with_pop_rx):
    # Test both NX-based and RX-based Graph objects
    do_test_recursive_seed_part_uses_method(twelve_by_twelve_with_pop_nx)
    do_test_recursive_seed_part_uses_method(twelve_by_twelve_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_recursive_seed_part_with_n_unspecified_within_epsilon(
    twelve_by_twelve_with_pop_graph,
):
    n_districts = 6  # This should set n=3
    ideal_pop = (
        sum(
            twelve_by_twelve_with_pop_graph.node_data(node)["pop"]
            for node in twelve_by_twelve_with_pop_graph
        )
    ) / n_districts
    epsilon = 0.05
    result = recursive_seed_part(
        twelve_by_twelve_with_pop_graph,
        range(n_districts),
        ideal_pop,
        "pop",
        epsilon,
        ceil=None,
    )
    partition = Partition(
        twelve_by_twelve_with_pop_graph, result, updaters={"pop": Tally("pop")}
    )
    # frm: Original Code:
    #
    #    return all(
    #        abs(part_pop - ideal_pop) / ideal_pop < epsilon
    #        for part_pop in partition["pop"].values()
    #    )
    assert all(
        abs(part_pop - ideal_pop) / ideal_pop < epsilon
        for part_pop in partition["pop"].values()
    )

def test_recursive_seed_part_with_n_unspecified_within_epsilon(
  twelve_by_twelve_with_pop_nx,
  twelve_by_twelve_with_pop_rx
):
    # Test both NX-based and RX-based Graph objects
    do_test_recursive_seed_part_with_n_unspecified_within_epsilon(twelve_by_twelve_with_pop_nx)
    do_test_recursive_seed_part_with_n_unspecified_within_epsilon(twelve_by_twelve_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_random_spanning_tree_returns_tree_with_pop_attribute(graph):
    tree = random_spanning_tree(graph)
    # frm: Original code:    assert networkx.is_tree(tree)
    assert tree.is_a_tree()

def test_random_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop_nx, graph_with_pop_rx):
    # Test both NX-based and RX-based Graph objects
    do_test_random_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop_nx)
    do_test_random_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_uniform_spanning_tree_returns_tree_with_pop_attribute(graph):
    tree = uniform_spanning_tree(graph)
    # frm: Original code:    assert networkx.is_tree(tree)
    assert tree.is_a_tree()

def test_uniform_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop_nx, graph_with_pop_rx):
    # Test both NX-based and RX-based Graph objects
    do_test_uniform_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop_nx)
    do_test_uniform_spanning_tree_returns_tree_with_pop_attribute(graph_with_pop_rx)

# ---------------------------------------------------------------------

def do_test_bipartition_tree_returns_a_tree(graph, spanning_tree):
    ideal_pop = sum(graph.node_data(node)["pop"] for node in graph) / 2

    result = bipartition_tree(
        graph, "pop", ideal_pop, 0.25, 10, spanning_tree, lambda x: 4
    )

    # frm: Original code:
    #    assert networkx.is_tree(spanning_tree.subgraph(result))
    #    assert networkx.is_tree(
    #        spanning_tree.subgraph({node for node in tree if node not in result})
    #    )
    assert spanning_tree.subgraph(result).is_a_tree()
    assert spanning_tree.subgraph({node for node in spanning_tree if node not in result}).is_a_tree()

def create_graphs_from_nx_edges(list_of_edges_nx, nx_to_rx_node_id_map):

    # NX is easy - just use the lsit of NX edges
    graph_nx = Graph.from_networkx(networkx.Graph(list_of_edges_nx))

    print(f"create_graphs_from_nx_edges: list_of_edges_nx is: {list_of_edges_nx}")
    print(f"create_graphs_from_nx_edges: nx_to_rx_node_id_map: {nx_to_rx_node_id_map}")

    # RX requires more work.  First we have to translate the node_ids used in the
    # list of edges to be the ones used in the RX graph using the
    # nx_to_rx_node_id_map.  Then we need to create a rustworkx.PyGraph and then
    # from that create a "new" Graph object.

    rx_graph = rustworkx.PyGraph()

    # translate the NX edges into the appropriate node_ids for the derived RX graph
    empty_edge_data_dict = {}  # needed so we can attach edge data to each edge
    list_of_edges_rx = [
      (
        nx_to_rx_node_id_map[edge[0]],
        nx_to_rx_node_id_map[edge[1]],
        empty_edge_data_dict
      ) 
      for edge in list_of_edges_nx
    ]
    rx_graph = rustworkx.PyGraph();

    # Create the RX nodes
    for i in range(9):
        empty_node_data_dict = {}  # needed so we can attach node data to each node
        rx_graph.add_node(empty_node_data_dict)
    # Verify that the nodes created have node_ids 0-8
    assert(set(rx_graph.node_indices()) == set(range(9)))

    # Add the RX edges
    rx_graph.add_edges_from(list_of_edges_rx)
    graph_rx = Graph.from_rustworkx(rx_graph)

    return graph_nx, graph_rx

def test_bipartition_tree_returns_a_tree(graph_with_pop_nx, graph_with_pop_rx):
    # Test both NX-based and RX-based Graph objects

    spanning_tree_edges_nx = [(0, 1), (1, 2), (1, 4), (3, 4), (4, 5), (3, 6), (6, 7), (6, 8)]

    spanning_tree_nx, spanning_tree_rx = \
      create_graphs_from_nx_edges(
        spanning_tree_edges_nx, 
        graph_with_pop_rx.nx_to_rx_node_id_map
      )

    # Give the nodes a population
    for node in spanning_tree_nx:
        spanning_tree_nx.node_data(node)["pop"] = 1
    for node in spanning_tree_rx:
        spanning_tree_rx.node_data(node)["pop"] = 1

    do_test_bipartition_tree_returns_a_tree(graph_with_pop_nx, spanning_tree_nx)
    do_test_bipartition_tree_returns_a_tree(graph_with_pop_rx, spanning_tree_rx)

def test_recom_works_as_a_proposal(partition_with_pop):
    graph = partition_with_pop.graph
    ideal_pop = sum(graph.node_data(node)["pop"] for node in graph) / 2
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
    ideal_pop = sum(graph.node_data(node)["pop"] for node in graph) / 2
    proposal = functools.partial(
        reversible_recom, pop_col="pop", pop_target=ideal_pop, epsilon=0.10, M=1
    )
    constraints = [within_percent_of_ideal_population(partition_with_pop, 0.25, "pop")]

    # frm: ???:  I am not sure how epsilon of 0.10 interacts with the constraint.
    #
    # The issue is that there are 9 nodes each with a population of 1, so the ideal population
    # is 4.5.  But no matter how you split the graph, you end up with an integer population, say, 
    # 4 or 5 - so you will never get within 0.10 of 4.5.  
    #
    # I am not quite sure what is being tested here...
    #
    # within_percent_of_ideal_population() returns a Bounds object which contains the lower and 
    # upper bounds for a given value - in this case 0.25 percent of the ideal population.
    #
    # The more I did into this the more I shake my head.  The value of "epsilon" passed into the 
    # reversible_recom() seems to only ever be used when creating a PopulatedGraph which in turn
    # only ever uses it when doing a specific balanced edge cut algorithm.  That is, the value of
    # epsilon is very rarely used, and yet it is passed in as one of the important paramters to
    # reversible_recom().  It looks like the original coders thought that it would be a great thing
    # to have in the PopulatedGraph object, but then they didn't actually use it.  *sigh*
    #
    # Then this test defines a constraint for population defining it to be OK if the population
    # is within 25% of ideal - which is at odds with the value of epsilon above of 10%, but since
    # the value of epsilon (of 10%) is never used, whatever...
    #

    # frm: TODO:  Grok this test - what is it trying to accomplish?
    #
    # The proposal uses reversible_recom() with the default value for the "repeat_until_valid" 
    # parameter which is False.  This means that the call to try to combine and then split two
    # parts (districts) only gets one shot at it before it fails.  In this case, that means that
    # it fails EVERY time - because the initial spanning tree that is returned is not balanced
    # enough to satisfy the population constraint.  If you let it run, then it succeeds after 
    # a couple of attempts (I think 10), but it never succeeds on the first try, and there is no
    # randomness possible since we only have two parts (districts) that we can merge.
    #
    # So this test runs through 100 chain iterations doing NOTHING - returning the same partition
    # each iteration, and in fact returning the same partition at the end that it started with.
    #
    # This raises all sorts of issues:
    #
    #   * Makes no sense for this test
    #   * Questions the logic in reversible_recom() to not detect an infinite loop
    #   * Questions the logic that does not inform the user somehow that the chain is ineffective
    #   * Raises the issue of documentation of the code - it took me quite a long time to
    #     figure out WTF was going on...
    #


    chain = MarkovChain(proposal, constraints, lambda x: True, partition_with_pop, 100)

    for state in chain:
        assert contiguous(state)

# frm: TODO:  Add more tests using MarkovChain...

def test_find_balanced_cuts_contraction():

    # frm: TODO:  Add test for RX-based Graph object

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

    list_of_nodes_nx = ([(0, 1), (1, 2), (2, 3), (3, 4)])

    # For this test we are not dealing with an RX-based Graph object
    # that is derived fromn an NX-based Graph object, so the
    # nx_to_rx_node_id_map can just be the identity map...
    #
    nx_to_rx_node_id_map = { node: node for node in range(5) }

    tree_nx, tree_rx = \
      create_graphs_from_nx_edges(
        list_of_nodes_nx, 
        nx_to_rx_node_id_map
      )

    # OK to use the same populations for NX and RX graphs
    populations = {0: 4, 1: 4, 2: 3, 3: 3, 4: 3}

    populated_tree_nx = PopulatedGraph(
        graph=tree_nx, populations=populations, ideal_pop=10, epsilon=0.1
    )
    populated_tree_rx = PopulatedGraph(
        graph=tree_rx, populations=populations, ideal_pop=10, epsilon=0.1
    )

    cuts_nx = find_balanced_edge_cuts_contraction(populated_tree_nx, one_sided_cut=False)
    assert cuts_nx == []

    cuts_rx = find_balanced_edge_cuts_contraction(populated_tree_rx, one_sided_cut=False)
    assert cuts_rx == []


def test_find_balanced_cuts_memo():

    list_of_nodes_nx = [(0, 1), (1, 2), (1, 4), (3, 4), (4, 5), (3, 6), (6, 7), (6, 8)]

    # For this test we are not dealing with an RX-based Graph object
    # that is derived fromn an NX-based Graph object, so the
    # nx_to_rx_node_id_map can just be the identity map...
    #
    nx_to_rx_node_id_map = { node: node for node in range(9) }

    tree_nx, tree_rx = \
      create_graphs_from_nx_edges(
        list_of_nodes_nx, 
        nx_to_rx_node_id_map
      )

    # 0 - 1 - 2
    #     |
    #     4 - 3
    #     |   |
    #     5   6 - 7
    #         |
    #         8

    populated_tree_nx = PopulatedGraph(
        tree_nx, {node: 1 for node in tree_nx}, len(tree_nx) / 2, 0.5
    )
    populated_tree_rx = PopulatedGraph(
        tree_rx, {node: 1 for node in tree_rx}, len(tree_rx) / 2, 0.5
    )

    cuts_nx = find_balanced_edge_cuts_memoization(populated_tree_nx)
    edges_nx = set(tuple(sorted(cut.edge)) for cut in cuts_nx)
    assert edges_nx == {(1, 4), (3, 4), (3, 6)}

    cuts_rx = find_balanced_edge_cuts_memoization(populated_tree_rx)
    edges_rx = set(tuple(sorted(cut.edge)) for cut in cuts_rx)
    assert edges_rx == {(1, 4), (3, 4), (3, 6)}


def test_no_balanced_cuts_memo_when_one_side_okay():

    list_of_nodes_nx = ([(0, 1), (1, 2), (2, 3), (3, 4)])

    # For this test we are not dealing with an RX-based Graph object
    # that is derived fromn an NX-based Graph object, so the
    # nx_to_rx_node_id_map can just be the identity map...
    #
    nx_to_rx_node_id_map = { node: node for node in range(5) }

    tree_nx, tree_rx = \
      create_graphs_from_nx_edges(
        list_of_nodes_nx, 
        nx_to_rx_node_id_map
      )

    # OK to use the same populations with both NX and RX Graphs
    populations = {0: 4, 1: 4, 2: 3, 3: 3, 4: 3}

    populated_tree_nx = PopulatedGraph(
        graph=tree_nx, populations=populations, ideal_pop=10, epsilon=0.1
    )
    populated_tree_rx = PopulatedGraph(
        graph=tree_rx, populations=populations, ideal_pop=10, epsilon=0.1
    )

    cuts_nx = find_balanced_edge_cuts_memoization(populated_tree_nx)
    assert cuts_nx == []

    cuts_rx = find_balanced_edge_cuts_memoization(populated_tree_rx)
    assert cuts_rx == []


def test_prime_bound():
    assert (
        get_max_prime_factor_less_than(2024, 20) == 11
        and get_max_prime_factor_less_than(2024, 1) == None
        and get_max_prime_factor_less_than(2024, 2000) == 23
        and get_max_prime_factor_less_than(2024, -1) == None
    )



