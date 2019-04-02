import json
import pathlib
from tempfile import TemporaryDirectory

import networkx
import pytest

from gerrychain.partition import GeographicPartition, Partition
from gerrychain.proposals import propose_random_flip
from gerrychain.updaters import cut_edges


def test_Partition_can_be_flipped(example_partition):
    flip = {1: 2}
    new_partition = example_partition.flip(flip)
    assert new_partition.assignment[1] == 2


def test_Partition_misnamed_vertices_raises_keyerror():
    graph = networkx.complete_graph(3)
    assignment = {"0": 1, "1": 1, "2": 2}
    with pytest.raises(KeyError):
        Partition(graph, assignment, {"cut_edges": cut_edges})


def test_Partition_unlabelled_vertices_raises_keyerror():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 2: 2}
    with pytest.raises(KeyError):
        Partition(graph, assignment, {"cut_edges": cut_edges})


def test_Partition_knows_cut_edges_K3(example_partition):
    partition = example_partition
    assert (1, 2) in partition["cut_edges"] or (2, 1) in partition["cut_edges"]
    assert (0, 2) in partition["cut_edges"] or (2, 0) in partition["cut_edges"]


def test_propose_random_flip_proposes_a_partition(example_partition):
    partition = example_partition
    proposal = propose_random_flip(partition)
    assert isinstance(proposal, partition.__class__)


@pytest.fixture
def example_geographic_partition():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}
    for node in graph.nodes:
        graph.node[node]["boundary_node"] = False
        graph.node[node]["area"] = 1
    for edge in graph.edges:
        graph.edges[edge]["shared_perim"] = 1
    return GeographicPartition(graph, assignment, None, None, None)


def test_geographic_partition_can_be_instantiated(example_geographic_partition):
    partition = example_geographic_partition
    assert partition.updaters == GeographicPartition.default_updaters


def test_Partition_parts_is_a_dictionary_of_parts_to_nodes(example_partition):
    partition = example_partition
    flip = {1: 2}
    new_partition = partition.flip(flip)
    assert all(isinstance(nodes, frozenset) for nodes in new_partition.parts.values())
    assert all(isinstance(nodes, frozenset) for nodes in partition.parts.values())


def test_Partition_has_subgraphs(example_partition):
    partition = example_partition
    assert set(partition.subgraphs[1].nodes) == {0, 1}
    assert set(partition.subgraphs[2].nodes) == {2}
    assert len(list(partition.subgraphs)) == 2


def test_Partition_caches_subgraphs(example_partition):
    subgraph = example_partition.subgraphs[1]
    assert subgraph is example_partition.subgraphs[1]


def test_partition_implements_getattr_for_updater_access(example_partition):
    assert example_partition.cut_edges


def test_can_be_created_from_a_districtr_file(graph, districtr_plan_file):
    for node in graph:
        graph.nodes[node]["area_num_1"] = node

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
