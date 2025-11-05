import math

import networkx
import pytest

from gerrychain import MarkovChain
from gerrychain.constraints import Validator, no_vanishing_districts
from gerrychain.graph import Graph
from gerrychain.partition import Partition
from gerrychain.proposals import propose_random_flip
import random
from gerrychain.updaters import (Election, Tally, boundary_nodes, cut_edges,
                                 cut_edges_by_part, exterior_boundaries,
                                 exterior_boundaries_as_a_set,
                                 interior_boundaries, perimeter)
from gerrychain.updaters.election import ElectionResults
random.seed(2018)

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

    party_names_to_node_attribute_names = ["D", "R"]

    election = Election("Mock Election", party_names_to_node_attribute_names)
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
    nx_graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}

    nx_graph.nodes[0]["stat"] = 1
    nx_graph.nodes[1]["stat"] = 2
    nx_graph.nodes[2]["stat"] = 7

    graph = Graph.from_networkx(nx_graph)

    updaters = {"total_stat": Tally("stat", alias="total_stat")}

    # This test is complicated by the fact that "original" node_ids are typically based
    # on the node_ids for NX-based graphs, so in this test's case, those would be: 0, 1, 2 .
    # However, when we create a Partition, we convert to an RX-based graph object and 
    # as a result the internal node_ids for the RX-based graph change.  So, when we ask
    # for graph data from a partition we need to be careful to use its internal node_ids.

    # Verify that the "total_stat" for the part (district) 2 is 7
    partition = Partition(graph, assignment, updaters)
    assert partition["total_stat"][2] == 7

    # Flip node with original node_id of 1 to be in part (district) 2
    flip = {1: 2}

    new_partition = partition.flip(flip, use_original_nx_node_ids=True)

    assert new_partition["total_stat"][2] == 9


def test_tally_multiple_node_attribute_names(graph_with_d_and_r_cols):
    graph = graph_with_d_and_r_cols

    updaters = {"total": Tally(["D", "R"], alias="total")}
    assignment = {i: 1 if i in range(4) else 2 for i in range(9)}

    partition = Partition(graph, assignment, updaters)
    expected_total_in_district_one = sum(
        graph.node_data(i)["D"] + graph.node_data(i)["R"] for i in range(4)
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
        for col in election.node_attribute_names:
            graph.node_data(node)[col] = 0

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


def _convert_dict_of_set_of_rx_node_ids_to_set_of_nx_node_ids(dict_of_set_of_rx_nodes, nx_to_rx_node_id_map):

    # frm: TODO:  This way to convert node_ids is clumsy and inconvenient.  Think of something better...

    # When we create a partition from an NX based Graph we convert it to be an 
    # RX based Graph which changes the node_ids of the graph.  If one wants
    # to convert sets of RX based graph node_ids back to the node_ids in the
    # original NX Graph, then we can do so by taking advantage of the 
    # nx_to_rx_node_id_map that is generated and saved when we converted the
    # NX based graph to be based on RX
    #
    # This routine converts the data that some updaters create - namely a mapping from
    # partitions to a set of node_ids.

    converted_set = {}
    if nx_to_rx_node_id_map is not None:    # means graph was converted from NX
        # reverse the map
        rx_to_nx_node_id_map = {value: key for key, value in nx_to_rx_node_id_map.items()}
        converted_set = {}
        for part, set_of_rx_nodes in dict_of_set_of_rx_nodes.items():
            converted_set_of_rx_nodes = {rx_to_nx_node_id_map[rx_node_id] for rx_node_id in set_of_rx_nodes}
            converted_set[part] = converted_set_of_rx_nodes
        # converted_set = {
        #   part: {rx_to_nx_node_id_map[rx_node_id]}
        #   for part, set_of_rx_node_ids in dict_of_set_of_rx_nodes.items()
        #   for rx_node_id in set_of_rx_node_ids
        # }
    return converted_set

def test_exterior_boundaries_as_a_set(three_by_three_grid):
    graph = three_by_three_grid

    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        graph.node_data(i)["boundary_node"] = True
    graph.node_data(4)["boundary_node"] = False

    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {
        "exterior_boundaries_as_a_set": exterior_boundaries_as_a_set,
        "boundary_nodes": boundary_nodes,
    }
    partition = Partition(graph, assignment, updaters)

    result = partition["exterior_boundaries_as_a_set"]

    # frm: TOdO: Come up with a nice way to convert the result which uses
    #               RX based node_ids back to the original NX based node_ids...

    # If the original graph that the partition was based on was an NX graph
    # then we need to convert the RX node_ids in the partition's graph
    # back to what they were in the NX graph.
    nx_to_rx_node_id_map = partition.graph.get_nx_to_rx_node_id_map()
    if nx_to_rx_node_id_map is not None:
        converted_result = _convert_dict_of_set_of_rx_node_ids_to_set_of_nx_node_ids(result, nx_to_rx_node_id_map)
        result = converted_result

    assert result[1] == {0, 1, 3} and result[2] == {2, 5, 6, 7, 8}

    # Flip nodes and then recompute partition
    # boundaries to make sure the updater works properly.  
    # The new partition map will look like this:
    #
    #   112    111
    #   112 -> 121
    #   222    222
    #
    # In terms of the original NX graph's node_ids, we would 
    # do the following flips: 4->2, 2->1, and 5->1
    #
    # However, the node_ids in the partition's graph have changed due to 
    # conversion to RX, so we need to translate the flips into RX node_ids
    
    nx_flips = {4: 2, 2: 1, 5: 1}
    rx_to_nx_node_id_map = {v: k for k,v in nx_to_rx_node_id_map.items()}
    rx_flips = {rx_to_nx_node_id_map[nx_node_id]: part for nx_node_id, part in nx_flips.items()}

    new_partition = Partition(parent=partition, flips=rx_flips)

    result = new_partition["exterior_boundaries_as_a_set"]

    # If the original graph that the partition was based on was an NX graph
    # then we need to convert the RX node_ids in the partition's graph
    # back to what they were in the NX graph.
    nx_to_rx_node_id_map = new_partition.graph.get_nx_to_rx_node_id_map()
    if nx_to_rx_node_id_map is not None:
        converted_result = _convert_dict_of_set_of_rx_node_ids_to_set_of_nx_node_ids(result, nx_to_rx_node_id_map)
        result = converted_result

    assert result[1] == {0, 1, 2, 3, 5} and result[2] == {6, 7, 8}


def test_exterior_boundaries(three_by_three_grid):

    graph = three_by_three_grid

    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        graph.node_data(i)["boundary_node"] = True
        graph.node_data(i)["boundary_perim"] = 2
    graph.node_data(4)["boundary_node"] = False

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

    # Convert the flips into internal node_ids
    internal_flips = {}
    for node_id, part in flips.items():
        internal_node_id = partition.graph.internal_node_id_for_original_nx_node_id(node_id)
        internal_flips[internal_node_id] = part

    new_partition = Partition(parent=partition, flips=internal_flips)

    result = new_partition["exterior_boundaries"]

    assert result[1] == 10 and result[2] == 6


def test_perimeter(three_by_three_grid):
    graph = three_by_three_grid
    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        graph.node_data(i)["boundary_node"] = True
        # frm: TODO:  Update test - boundary_perim should be 2 for corner nodes...
        graph.node_data(i)["boundary_perim"] = 1
    graph.node_data(4)["boundary_node"] = False

    for edge in graph.edges:
        graph.edge_data(edge)["shared_perim"] = 1

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


def expected_tally(partition, node_attribute_name):
    return {
        part: sum(partition.graph.node_data(node)[node_attribute_name] for node in nodes)
        for part, nodes in partition.parts.items()
    }
