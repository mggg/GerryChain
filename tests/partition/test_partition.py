import json
import pathlib
from tempfile import TemporaryDirectory

import networkx
import pytest

from gerrychain.partition import GeographicPartition, Partition
from gerrychain.proposals import propose_random_flip
from gerrychain.graph import Graph
from gerrychain.updaters import cut_edges


def test_Partition_can_be_flipped(example_partition):
    # frm: TODO:  Verify that this flip is in internal RX-based graph node_ids and not "original" NX node_ids
    #
    # My guess is that this flip is intended to be in original node_ids but that the test works
    # anyways because the assertion uses the same numbers.  It should probably be changed to use
    # original node_ids and to translate the node_id and part in the assert into internal node_ids
    # just to make it crystal clear to anyone following later what is going on...

    flip = {1: 2}
    new_partition = example_partition.flip(flip)
    assert new_partition.assignment[1] == 2


def test_Partition_misnamed_vertices_raises_keyerror():
    graph = Graph.from_networkx(networkx.complete_graph(3))
    assignment = {"0": 1, "1": 1, "2": 2}
    with pytest.raises(KeyError):
        Partition(graph, assignment, {"cut_edges": cut_edges})


def test_Partition_graph_raises_typeerror():
    assignment = {"0": 1, "1": 1, "2": 2}
    with pytest.raises(TypeError):
        Partition("not a graph", assignment, {"cut_edges": cut_edges})


def test_Partition_unlabelled_vertices_raises_keyerror():
    graph = Graph.from_networkx(networkx.complete_graph(3))
    assignment = {0: 1, 2: 2}
    with pytest.raises(KeyError):
        Partition(graph, assignment, {"cut_edges": cut_edges})


def test_Partition_knows_cut_edges_K3(example_partition):
    partition = example_partition
    assert (1, 2) in partition["cut_edges"] or (2, 1) in partition["cut_edges"]
    assert (0, 2) in partition["cut_edges"] or (2, 0) in partition["cut_edges"]


def test_propose_random_flip_proposes_a_partition(example_partition):
    partition = example_partition

    # frm: TODO:  Verify that propose_random_flip() to make sure it is doing the right thing
    #               wrt RX-based node_ids vs. original node_ids.
    proposal = propose_random_flip(partition)
    assert isinstance(proposal, partition.__class__)


@pytest.fixture
def example_geographic_partition():
    graph = Graph.from_networkx(networkx.complete_graph(3))
    assignment = {0: 1, 1: 1, 2: 2}
    for node in graph.nodes:
        graph.node_data(node)["boundary_node"] = False
        graph.node_data(node)["area"] = 1
    for edge in graph.edges:
        graph.edge_data(edge)["shared_perim"] = 1
    return GeographicPartition(graph, assignment, None, None, None)


def test_geographic_partition_can_be_instantiated(example_geographic_partition):
    partition = example_geographic_partition
    assert isinstance(partition, GeographicPartition)


def test_Partition_parts_is_a_dictionary_of_parts_to_nodes(example_partition):
    partition = example_partition
    flip = {1: 2}
    new_partition = partition.flip(flip, use_original_node_ids=True)
    assert all(isinstance(nodes, frozenset) for nodes in new_partition.parts.values())
    assert all(isinstance(nodes, frozenset) for nodes in partition.parts.values())


def test_Partition_has_subgraphs(example_partition):
    partition = example_partition
    assert set(partition.subgraphs[1].nodes) == {0, 1}
    # frm: TODO:  NX vs. RX node_id issues here...
    #                   The following statement fails because nodes are given new
    #                   node IDs in RX, so instead of having an ID of 2
    #                   the ID is 0.  Not sure right now what the right 
    #                   fix is - need to grok what this test is actually testing...
    #
    # I am going to assume that this test is just verifying that 
    # we correctly create the appropriate subgraphs (which we do).
    # Rewrite the test so that it first verifies the nodes in the parent graph
    # and their assignments, then reach into the subgraphs to verify that the 
    # parent node mapping for the subgraphs is correct.
    #
    assert set(partition.subgraphs[2].nodes) == {2}
    assert len(list(partition.subgraphs)) == 2


def test_Partition_caches_subgraphs(example_partition):
    subgraph = example_partition.subgraphs[1]
    assert subgraph is example_partition.subgraphs[1]


def test_partition_implements_getattr_for_updater_access(example_partition):
    assert example_partition.cut_edges


def test_can_be_created_from_a_districtr_file(graph, districtr_plan_file):
    for node in graph:
        graph.node_data(node)["area_num_1"] = node

    # frm: TODO:  NX vs. RX node_id issues here...

    partition = Partition.from_districtr_file(graph, districtr_plan_file)
    assert partition.assignment.to_dict() == {
        0: 1,
        1: 1,
        2: 1,
        3: 2,
        4: 2,
        5: 2,
        6: 3,
        7: 3,
        8: 3,
    }


def test_from_districtr_plan_raises_if_id_column_missing(graph, districtr_plan_file):
    with pytest.raises(TypeError):
        Partition.from_districtr_file(graph, districtr_plan_file)


@pytest.fixture
def districtr_plan_file():
    districtr_plan = {
        "assignment": {
            "0": 1,
            "1": 1,
            "2": 1,
            "3": 2,
            "4": 2,
            "5": 2,
            "6": 3,
            "7": 3,
            "8": 3,
        },
        "id": "f3087dd5",
        "idColumn": {"key": "area_num_1", "name": "Area Number"},
        "placeId": "three_by_three_grid",
        "problem": {
            "type": "multimember",
            "numberOfParts": 3,
            "name": "City Council",
            "pluralNoun": "City Council Seats",
        },
    }

    with TemporaryDirectory() as tempdir:
        filename = pathlib.Path(tempdir) / "districtr-plan.json"
        with open(filename, "w") as f:
            json.dump(districtr_plan, f)
        yield filename


def test_repr(example_partition):
    assert repr(example_partition) == "<Partition [2 parts]>"


def test_partition_has_default_updaters(example_partition):
    partition = example_partition
    should_have_updaters = {"cut_edges": cut_edges}

    for updater in should_have_updaters:
        assert should_have_updaters[updater](partition) == partition[updater]


def test_partition_has_keys(example_partition):
    assert "cut_edges" in set(example_partition.keys())


def test_geographic_partition_has_keys(example_geographic_partition):
    keys = set(example_geographic_partition.updaters.keys())

    assert "perimeter" in keys
    assert "exterior_boundaries" in keys
    assert "interior_boundaries" in keys
    assert "boundary_nodes" in keys
    assert "cut_edges" in keys
    assert "area" in keys
    assert "cut_edges_by_part" in keys


def test_geographic_partition_has_default_updaters(example_geographic_partition):
    assert hasattr(example_geographic_partition, "perimeter")
    assert hasattr(example_geographic_partition, "exterior_boundaries")
    assert hasattr(example_geographic_partition, "interior_boundaries")
    assert hasattr(example_geographic_partition, "boundary_nodes")
    assert hasattr(example_geographic_partition, "cut_edges")
    assert hasattr(example_geographic_partition, "area")
    assert hasattr(example_geographic_partition, "cut_edges_by_part")
