import math

import networkx
import pytest

from gerrychain import MarkovChain
from gerrychain.constraints import Validator, no_vanishing_districts
from gerrychain.partition import Partition
from gerrychain.proposals import propose_random_flip
from gerrychain.random import random
from gerrychain.updaters import (Election, Tally, boundary_nodes, cut_edges,
                                 cut_edges_by_part, exterior_boundaries,
                                 exterior_boundaries_as_a_set,
                                 interior_boundaries, perimeter)
from gerrychain.updaters.election import ElectionResults


@pytest.fixture
def graph_with_d_and_r_cols(graph_with_random_data_factory):
    return graph_with_random_data_factory(["D", "R"])


def random_assignment(graph, num_districts):
    assignment = {node: random.choice(range(num_districts)) for node in graph.nodes}
    # Make sure that there are cut edges:
    while len(set(assignment.values())) == 1:
        assignment = {node: random.choice(range(num_districts)) for node in graph.nodes}
    return assignment


@pytest.fixture
def partition_with_election(graph_with_d_and_r_cols):
    graph = graph_with_d_and_r_cols
    assignment = random_assignment(graph, 3)
    parties_to_columns = {
        "D": {node: graph.nodes[node]["D"] for node in graph.nodes},
        "R": {node: graph.nodes[node]["R"] for node in graph.nodes},
    }
    election = Election("Mock Election", parties_to_columns)
    updaters = {"Mock Election": election, "cut_edges": cut_edges}
    return Partition(graph, assignment, updaters)


@pytest.fixture
def chain_with_election(partition_with_election):
    return MarkovChain(
        propose_random_flip,
        Validator([no_vanishing_districts]),
        lambda x: True,
        partition_with_election,
        total_steps=10,
    )


def test_Partition_can_update_stats():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}

    graph.nodes[0]["stat"] = 1
    graph.nodes[1]["stat"] = 2
    graph.nodes[2]["stat"] = 3

    updaters = {"total_stat": Tally("stat", alias="total_stat")}

    partition = Partition(graph, assignment, updaters)
    assert partition["total_stat"][2] == 3
    flip = {1: 2}

    new_partition = partition.flip(flip)
    assert new_partition["total_stat"][2] == 5


def test_tally_multiple_columns(graph_with_d_and_r_cols):
    graph = graph_with_d_and_r_cols

    updaters = {"total": Tally(["D", "R"], alias="total")}
    assignment = {i: 1 if i in range(4) else 2 for i in range(9)}

    partition = Partition(graph, assignment, updaters)
    expected_total_in_district_one = sum(
        graph.nodes[i]["D"] + graph.nodes[i]["R"] for i in range(4)
    )
    assert partition["total"][1] == expected_total_in_district_one


def test_vote_totals_are_nonnegative(partition_with_election):
    partition = partition_with_election
    assert all(count >= 0 for count in partition["Mock Election"].totals.values())


def test_vote_proportion_updater_returns_percentage_or_nan(partition_with_election):
    partition = partition_with_election

    election_view = partition["Mock Election"]

    # The first update gives a percentage
    assert all(
        is_percentage_or_nan(value)
        for party_percents in election_view.percents_for_party.values()
        for value in party_percents.values()
    )


def test_vote_proportion_returns_nan_if_total_votes_is_zero(three_by_three_grid):
    election = Election("Mock Election", ["D", "R"], alias="election")
    graph = three_by_three_grid

    for node in graph.nodes:
        for col in election.columns:
            graph.nodes[node][col] = 0

    updaters = {"election": election}
    assignment = random_assignment(graph, 3)

    partition = Partition(graph, assignment, updaters)

    assert all(
        math.isnan(value)
        for party_percents in partition["election"].percents_for_party.values()
        for value in party_percents.values()
    )


def is_percentage_or_nan(value):
    return (0 <= value and value <= 1) or math.isnan(value)


def test_vote_proportion_updater_returns_percentage_or_nan_on_later_steps(
    chain_with_election
):
    for partition in chain_with_election:
        election_view = partition["Mock Election"]
        assert all(
            is_percentage_or_nan(value)
            for party_percents in election_view.percents_for_party.values()
            for value in party_percents.values()
        )


def test_vote_proportion_field_has_key_for_each_district(partition_with_election):
    partition = partition_with_election
    for percents in partition["Mock Election"].percents_for_party.values():
        assert set(percents.keys()) == set(partition.parts)


def test_vote_proportions_sum_to_one(partition_with_election):
    partition = partition_with_election
    election_view = partition["Mock Election"]

    for part in partition.parts:
        total_percent = sum(
            percents[part] for percents in election_view.percents_for_party.values()
        )
        assert abs(1 - total_percent) < 0.001


def test_election_result_has_a_cute_str_method():
    election = Election(
        "2008 Presidential", {"Democratic": [3, 1, 2], "Republican": [1, 2, 1]}
    )
    results = ElectionResults(
        election,
        {"Democratic": {0: 3, 1: 1, 2: 2}, "Republican": {0: 1, 1: 2, 2: 1}},
        [0, 1, 2],
    )
    expected = (
        "Election Results for 2008 Presidential\n"
        "0:\n"
        "  Democratic: 0.75\n"
        "  Republican: 0.25\n"
        "1:\n"
        "  Democratic: 0.3333\n"
        "  Republican: 0.6667\n"
        "2:\n"
        "  Democratic: 0.6667\n"
        "  Republican: 0.3333"
    )
    assert str(results) == expected


def test_exterior_boundaries_as_a_set(three_by_three_grid):
    graph = three_by_three_grid

    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        graph.nodes[i]["boundary_node"] = True
    graph.nodes[4]["boundary_node"] = False

    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {
        "exterior_boundaries_as_a_set": exterior_boundaries_as_a_set,
        "boundary_nodes": boundary_nodes,
    }
    partition = Partition(graph, assignment, updaters)

    result = partition["exterior_boundaries_as_a_set"]
    assert result[1] == {0, 1, 3} and result[2] == {2, 5, 6, 7, 8}

    # 112    111
    # 112 -> 121
    # 222    222
    flips = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flips)

    result = new_partition["exterior_boundaries_as_a_set"]

    assert result[1] == {0, 1, 2, 3, 5} and result[2] == {6, 7, 8}


def test_exterior_boundaries(three_by_three_grid):
    graph = three_by_three_grid

    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        graph.nodes[i]["boundary_node"] = True
        graph.nodes[i]["boundary_perim"] = 2
    graph.nodes[4]["boundary_node"] = False

    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {
        "exterior_boundaries": exterior_boundaries,
        "boundary_nodes": boundary_nodes,
    }
    partition = Partition(graph, assignment, updaters)

    result = partition["exterior_boundaries"]
    assert result[1] == 6 and result[2] == 10

    # 112    111
    # 112 -> 121
    # 222    222
    flips = {4: 2, 2: 1, 5: 1}

    new_partition = Partition(parent=partition, flips=flips)

    result = new_partition["exterior_boundaries"]

    assert result[1] == 10 and result[2] == 6


def test_perimeter(three_by_three_grid):
    graph = three_by_three_grid
    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        graph.nodes[i]["boundary_node"] = True
        graph.nodes[i]["boundary_perim"] = 1
    graph.nodes[4]["boundary_node"] = False

    for edge in graph.edges:
        graph.edges[edge]["shared_perim"] = 1

    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {
        "exterior_boundaries": exterior_boundaries,
        "interior_boundaries": interior_boundaries,
        "cut_edges_by_part": cut_edges_by_part,
        "boundary_nodes": boundary_nodes,
        "perimeter": perimeter,
    }
    partition = Partition(graph, assignment, updaters)

    # 112
    # 112
    # 222

    result = partition["perimeter"]

    assert result[1] == 3 + 4  # 3 nodes + 4 edges
    assert result[2] == 5 + 4  # 5 nodes + 4 edges


def reject_half_of_all_flips(partition):
    if partition.parent is None:
        return True
    return random.random() > 0.5


def test_elections_match_the_naive_computation(partition_with_election):
    chain = MarkovChain(
        propose_random_flip,
        Validator([no_vanishing_districts, reject_half_of_all_flips]),
        lambda x: True,
        partition_with_election,
        total_steps=100,
    )

    for partition in chain:
        election_view = partition["Mock Election"]
        expected_party_totals = {
            "D": expected_tally(partition, "D"),
            "R": expected_tally(partition, "R"),
        }
        assert expected_party_totals == election_view.totals_for_party


def expected_tally(partition, column):
    return {
        part: sum(partition.graph.nodes[node][column] for node in nodes)
        for part, nodes in partition.parts.items()
    }
