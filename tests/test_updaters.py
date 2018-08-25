import json
import math
import random

import geopandas as gp
import networkx
import pytest

from rundmcmc.chain import MarkovChain
from rundmcmc.make_graph import get_assignment_dict_from_df
from rundmcmc.partition import Partition
from rundmcmc.proposals import propose_random_flip
from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               interior_boundaries,
                               exterior_boundaries_as_a_set,
                               perimeters, Election)
from rundmcmc.updaters.election import ElectionResults
from rundmcmc.validity import (Validator, contiguous, no_vanishing_districts,
                               single_flip_contiguous)


@pytest.fixture
def graph_with_d_and_r_cols(graph_with_random_data_factory):
    return graph_with_random_data_factory(['D', 'R'])


def random_assignment(graph, num_districts):
    return {node: random.choice(range(num_districts)) for node in graph.nodes}


@pytest.fixture
def partition_with_election(graph_with_d_and_r_cols):
    graph = graph_with_d_and_r_cols
    assignment = random_assignment(graph, 3)
    parties_to_columns = {
        'D': {node: graph.nodes[node]['D'] for node in graph.nodes},
        'R': {node: graph.nodes[node]['R'] for node in graph.nodes}
    }
    election = Election("Mock Election", parties_to_columns)
    updaters = {"Mock Election": election}
    return Partition(graph, assignment, updaters)


def test_Partition_can_update_stats():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}

    graph.nodes[0]['stat'] = 1
    graph.nodes[1]['stat'] = 2
    graph.nodes[2]['stat'] = 3

    updaters = {'total_stat': Tally('stat', alias='total_stat')}

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
    assignment = get_assignment_dict_from_df(df, "GEOID10", "CD")

    validator = Validator([equality_validator])
    updaters = {"contiguous": contiguous, "cut_edges": cut_edges,
        "flip_check": single_flip_contiguous}

    initial_partition = Partition(graph, assignment, updaters)
    accept = lambda x: True

    chain = MarkovChain(propose_random_flip, validator, accept, initial_partition, total_steps=100)
    list(chain)


def test_tally_multiple_columns(graph_with_d_and_r_cols):
    graph = graph_with_d_and_r_cols

    updaters = {'total': Tally(['D', 'R'], alias='total')}
    assignment = {i: 1 if i in range(4) else 2 for i in range(9)}

    partition = Partition(graph, assignment, updaters)
    expected_total_in_district_one = sum(
        graph.nodes[i]['D'] + graph.nodes[i]['R'] for i in range(4))
    assert partition['total'][1] == expected_total_in_district_one


def test_vote_totals_are_nonnegative(partition_with_election):
    partition = partition_with_election
    assert all(count >= 0 for count in partition['Mock Election'].totals.values())


def test_vote_proportion_updater_returns_percentage_or_nan(partition_with_election):
    partition = partition_with_election

    election_view = partition['Mock Election']

    # The first update gives a percentage
    assert all(is_percentage_or_nan(value)
               for party_percents in election_view.percents_for_party.values()
               for value in party_percents.values())


def test_vote_proportion_returns_nan_if_total_votes_is_zero(three_by_three_grid):
    election = Election("Mock Election", ['D', 'R'], alias='election')
    graph = three_by_three_grid

    for node in graph.nodes:
        for col in election.columns:
            graph.nodes[node][col] = 0

    updaters = {'election': election}
    assignment = random_assignment(graph, 3)

    partition = Partition(graph, assignment, updaters)

    assert all(math.isnan(value)
               for party_percents in partition['election'].percents_for_party.values()
               for value in party_percents.values())


def is_percentage_or_nan(value):
    return (0 <= value and value <= 1) or math.isnan(value)


def test_vote_proportion_updater_returns_percentage_or_nan_on_later_steps(partition_with_election):
    chain = MarkovChain(propose_random_flip, Validator([no_vanishing_districts]),
                        lambda x: True, partition_with_election, total_steps=10)

    for partition in chain:
        election_view = partition['Mock Election']
        assert all(is_percentage_or_nan(value)
                   for party_percents in election_view.percents_for_party.values()
                   for value in party_percents.values())


def test_vote_proportion_field_has_key_for_each_district(partition_with_election):
    partition = partition_with_election
    for percents in partition['Mock Election'].percents_for_party.values():
        assert set(percents.keys()) == set(partition.parts.keys())


def test_vote_proportions_sum_to_one(partition_with_election):
    partition = partition_with_election
    election_view = partition['Mock Election']

    for part in partition.parts:
        total_percent = sum(percents[part]
                            for percents in election_view.percents_for_party.values())
        assert abs(1 - total_percent) < 0.001


def test_election_result_has_a_cute_str_method():
    election = Election("2008 Presidential", {"Democratic": [3, 1, 2], "Republican": [1, 2, 1]})
    results = ElectionResults(election,
        {"Democratic": {0: 3, 1: 1, 2: 2}, "Republican": {0: 1, 1: 2, 2: 1}},
        {0: 4, 1: 3, 2: 3},
        {"Democratic": {0: 0.75, 1: 0.33, 2: 0.66}, "Republican": {0: 0.25, 1: 0.66, 2: 0.33}}
    )
    expected = "Election Results for 2008 Presidential\n" \
        "0:\n" \
        "  Democratic: 0.75\n" \
        "  Republican: 0.25\n" \
        "1:\n" \
        "  Democratic: 0.33\n" \
        "  Republican: 0.66\n" \
        "2:\n" \
        "  Democratic: 0.66\n" \
        "  Republican: 0.33"
    assert str(results) == expected


def test_exterior_boundaries_as_a_set(three_by_three_grid):
    graph = three_by_three_grid

    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        graph.nodes[i]['boundary_node'] = True
    graph.nodes[4]['boundary_node'] = False

    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {'exterior_boundaries_as_a_set': exterior_boundaries_as_a_set,
        'boundary_nodes': boundary_nodes}
    partition = Partition(graph, assignment, updaters)

    result = partition['exterior_boundaries_as_a_set']
    assert result[1] == {0, 1, 3} and result[2] == {2, 5, 6, 7, 8}

    # 112    111
    # 112 -> 121
    # 222    222
    flips = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flips)

    result = new_partition['exterior_boundaries_as_a_set']

    assert result[1] == {0, 1, 2, 3, 5} and result[2] == {6, 7, 8}


def test_exterior_boundaries(three_by_three_grid):
    graph = three_by_three_grid

    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        graph.nodes[i]['boundary_node'] = True
        graph.nodes[i]['boundary_perim'] = 2
    graph.nodes[4]['boundary_node'] = False

    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {'exterior_boundaries': exterior_boundaries,
        'boundary_nodes': boundary_nodes}
    partition = Partition(graph, assignment, updaters)

    result = partition['exterior_boundaries']
    assert result[1] == 6 and result[2] == 10

    # 112    111
    # 112 -> 121
    # 222    222
    flips = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flips)

    result = new_partition['exterior_boundaries']

    assert result[1] == 10 and result[2] == 6


def test_perimeters(three_by_three_grid):
    graph = three_by_three_grid
    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        graph.nodes[i]['boundary_node'] = True
        graph.nodes[i]['boundary_perim'] = 1
    graph.nodes[4]['boundary_node'] = False

    for edge in graph.edges:
        graph.edges[edge]['shared_perim'] = 1

    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {'exterior_boundaries': exterior_boundaries,
        'interior_boundaries': interior_boundaries,
        'cut_edges_by_part': cut_edges_by_part,
        'boundary_nodes': boundary_nodes, 'perimeters': perimeters}
    partition = Partition(graph, assignment, updaters)

    # 112
    # 112
    # 222

    result = partition['perimeters']

    assert result[1] == 3 + 4  # 3 nodes + 4 edges
    assert result[2] == 5 + 4  # 5 nodes + 4 edges
