import json
import math
import random

import geopandas as gp
import networkx

from rundmcmc.chain import MarkovChain
from rundmcmc.make_graph import get_assignment_dict
from rundmcmc.partition import Partition
from rundmcmc.proposals import propose_random_flip
from rundmcmc.updaters import cut_edges, tally_factory, votes_updaters
from rundmcmc.validity import Validator, contiguous, single_flip_contiguous
from rundmcmc.chain import MarkovChain
import geopandas as gp
import json


def three_by_three_grid():
    """Returns a graph that looks like this:
    0 1 2
    3 4 5
    6 7 8
    """
    graph = networkx.Graph()
    graph.add_edges_from([(0, 1), (0, 3), (1, 2), (1, 4), (2, 5), (3, 4),
                         (3, 6), (4, 5), (4, 7), (5, 8), (6, 7), (7, 8)])
    return graph


def edge_set_equal(set1, set2):
    return {(y, x) for x, y in set1} | set1 == {(y, x) for x, y in set2} | set2


def test_implementation_of_cut_edges_matches_naive_method():
    graph = three_by_three_grid()
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {'cut_edges': cut_edges}
    partition = Partition(graph, assignment, updaters)

    flip = {4: 2}
    new_partition = Partition(parent=partition, flips=flip)
    result = cut_edges(new_partition)

    naive_cut_edges = {edge for edge in graph.edges
                       if new_partition.crosses_parts(edge)}

    print(result)
    print(naive_cut_edges)

    assert edge_set_equal(result, naive_cut_edges)


def test_Partition_can_update_stats():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}

    graph.nodes[0]['stat'] = 1
    graph.nodes[1]['stat'] = 2
    graph.nodes[2]['stat'] = 3

    updaters = {'total_stat': tally_factory('stat', alias='total_stat')}

    partition = Partition(graph, assignment, updaters)
    assert partition['total_stat'][2] == 3
    flip = {1: 2}

    new_partition = partition.merge(flip)
    assert new_partition['total_stat'][2] == 5


# TODO: Make a smaller, easier to check test.
def test_single_flip_contiguity_equals_contiguity():
    import random
    random.seed(1887)

    def equality_validator(partition):
        val = partition["contiguous"] == partition["flip_check"]
        assert val
        return partition["contiguous"]

    df = gp.read_file("rundmcmc/testData/mo_cleaned_vtds.shp")

    with open("rundmcmc/testData/MO_graph.json") as f:
        graph_json = json.load(f)

    graph = networkx.readwrite.json_graph.adjacency_graph(graph_json)
    assignment = get_assignment_dict(df, "GEOID10", "CD")

    validator = Validator([equality_validator])
    updaters = {"contiguous": contiguous, "cut_edges": cut_edges,
        "flip_check": single_flip_contiguous}

    initial_partition = Partition(graph, assignment, updaters)
    accept = lambda x: True

    chain = MarkovChain(propose_random_flip, validator, accept, initial_partition, total_steps=100)
    list(chain)


def random_assignment(graph, num_districts):
    return {node: random.choice(range(num_districts)) for node in graph.nodes}


def setup_for_proportion_updaters(columns):
    graph = three_by_three_grid()

    attach_random_data(graph, columns)

    assignment = random_assignment(graph, 3)

    updaters = votes_updaters(columns)
    return Partition(graph, assignment, updaters)


def attach_random_data(graph, columns):
    for node in graph.nodes:
        for col in columns:
            graph.nodes[node][col] = random.randint(1, 1000)


def test_tally_multiple_columns():
    graph = three_by_three_grid()
    attach_random_data(graph, ['D', 'R'])
    updaters = {'total': tally_factory(['D', 'R'], alias='total')}
    assignment = {i: 1 if i in range(4) else 2 for i in range(9)}

    partition = Partition(graph, assignment, updaters)
    expected_total_in_district_one = sum(
        graph.nodes[i]['D'] + graph.nodes[i]['R'] for i in range(4))
    assert partition['total'][1] == expected_total_in_district_one


def test_vote_totals_are_positive():
    partition = setup_for_proportion_updaters(['D', 'R'])
    assert all(count > 0 for count in partition['total_votes'].values())


def test_vote_proportion_updater_returns_percentage():
    initial_partition = setup_for_proportion_updaters(['D', 'R'])

    # The first update gives a percentage
    assert all(0 <= value for value in initial_partition['D%'].values())
    assert all(value <= 1 for value in initial_partition['D%'].values())
    assert all(0 <= value for value in initial_partition['R%'].values())
    assert all(value <= 1 for value in initial_partition['R%'].values())


def test_vote_proportion_returns_nan_if_total_votes_is_zero():
    columns = ['D', 'R']
    graph = three_by_three_grid()
    for node in graph.nodes:
        for col in columns:
            graph.nodes[node][col] = 0
    updaters = votes_updaters(columns)
    assignment = random_assignment(graph, 3)

    partition = Partition(graph, assignment, updaters)

    assert all(math.isnan(value) for value in partition['D%'].values())
    assert all(math.isnan(value) for value in partition['R%'].values())


def test_vote_proportion_updater_returns_percentage_on_later_steps():
    columns = ['D', 'R']
    graph = three_by_three_grid()
    attach_random_data(graph, columns)
    assignment = random_assignment(graph, 3)
    updaters = {**votes_updaters(columns), 'cut_edges': cut_edges}

    initial_partition = Partition(graph, assignment, updaters)

    chain = MarkovChain(propose_random_flip, lambda x: True,
                        lambda x: True, initial_partition, total_steps=10)
    for partition in chain:
        assert all(0 < value for value in partition['D%'].values())
        assert all(value < 1 for value in partition['D%'].values())
        assert all(0 < value for value in partition['R%'].values())
        assert all(value < 1 for value in partition['R%'].values())


def test_vote_proportion_field_has_key_for_each_district():
    partition = setup_for_proportion_updaters(['D', 'R'])
    assert set(partition['D%'].keys()) == set(partition.parts.keys())


def test_vote_proportions_sum_to_one():
    partition = setup_for_proportion_updaters(['D', 'R'])

    assert all(abs(1 - partition['D%'][i] - partition['R%'][i]) < 0.001 for i in partition['D%'])
