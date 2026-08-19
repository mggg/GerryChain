import json
import pathlib
import random
from collections.abc import Iterator
from typing import cast
from tempfile import TemporaryDirectory

import networkx
import pytest
import gerrychain.rustworkx as rustworkx

from gerrychain.graph import Graph
from gerrychain.partition import GeographicPartition, Partition
from gerrychain.proposals import propose_random_flip
from gerrychain.updaters import cut_edges


def test_Partition_can_be_flipped(example_partition: Partition):
    # frm: TODO: Testing:  Verify that this flip is in internal RX-based graph node_ids and not "original" NX node_ids
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
        Partition(cast(Graph, "not a graph"), assignment, {"cut_edges": cut_edges})


def test_Partition_unlabelled_vertices_raises_keyerror():
    graph = Graph.from_networkx(networkx.complete_graph(3))
    assignment = {0: 1, 2: 2}
    with pytest.raises(KeyError):
        Partition(graph, assignment, {"cut_edges": cut_edges})


def test_assignment_vector(example_partition: Partition):
    assert example_partition.assignment_vector.tolist() == [1, 1, 2]


def test_assignment_vector_is_read_only(example_partition: Partition):
    with pytest.raises(ValueError):
        example_partition.assignment_vector[0] = 5


def test_assignment_vector_incremental_from_cached_parent(example_partition: Partition):
    parent_vector = example_partition.assignment_vector
    child = example_partition.flip({1: 2})
    assert child.assignment_vector.tolist() == [1, 2, 2]
    # The parent's cached vector is unchanged by the child's flips.
    assert parent_vector.tolist() == [1, 1, 2]


def test_assignment_vector_without_cached_parent(example_partition: Partition):
    child = example_partition.flip({1: 2})
    assert child.assignment_vector.tolist() == [1, 2, 2]


def test_assignment_vector_aligns_with_internal_node_ids():
    # String node labels, inserted in non-sorted order, so the internal rustworkx ids assigned
    # during conversion are decoupled from any natural ordering of the labels themselves.
    nx_graph = networkx.Graph()
    nx_graph.add_edges_from([("D", "A"), ("A", "C"), ("C", "B")])
    parts_by_label = {"D": 10, "A": 11, "C": 12, "B": 10}
    partition = Partition(Graph.from_networkx(nx_graph), parts_by_label, {"cut_edges": cut_edges})

    vector = partition.assignment_vector
    assert len(vector) == 4
    for label, part in parts_by_label.items():
        internal_id = partition.graph.internal_node_id_for_original_nx_node_id(label)
        assert vector[internal_id] == part

    # Position i is internal node id i, i.e. the graph's own node order.
    assert vector.tolist() == [partition.assignment[node] for node in partition.graph.nodes]

    # The incremental (copy-parent-and-apply-flips) path preserves the same alignment.
    flipped_id = partition.graph.internal_node_id_for_original_nx_node_id("B")
    child = partition.flip({flipped_id: 12})
    child_vector = child.assignment_vector
    for label, part in {**parts_by_label, "B": 12}.items():
        internal_id = partition.graph.internal_node_id_for_original_nx_node_id(label)
        assert child_vector[internal_id] == part


def test_assignment_vector_rejects_non_contiguous_graph():
    # Removing a node from a rustworkx graph leaves a hole in its node ids, so ascending id no
    # longer matches a dense 0..n-1 vector; emitting one must fail rather than misalign.
    rx_graph = rustworkx.PyGraph()
    a, b, c = rx_graph.add_nodes_from([{}, {}, {}])
    rx_graph.add_edges_from([(a, b, {}), (b, c, {})])
    rx_graph.remove_node(b)

    partition = Partition(Graph.from_rustworkx(rx_graph), {a: 1, c: 2}, {"cut_edges": cut_edges})
    with pytest.raises(ValueError, match="contiguous"):
        partition.assignment_vector


def test_Partition_knows_cut_edges_K3(example_partition: Partition):
    partition = example_partition
    assert (1, 2) in partition["cut_edges"] or (2, 1) in partition["cut_edges"]
    assert (0, 2) in partition["cut_edges"] or (2, 0) in partition["cut_edges"]


def test_propose_random_flip_proposes_a_partition(example_partition: Partition):
    partition = example_partition

    # frm: TODO: Testing:  Verify that propose_random_flip() to make sure it is doing the right thing
    #               wrt RX-based node_ids vs. original node_ids.
    proposal = propose_random_flip(partition, rng=random.Random(0))
    assert isinstance(proposal, partition.__class__)


@pytest.fixture
def example_geographic_partition() -> GeographicPartition:
    graph = Graph.from_networkx(networkx.complete_graph(3))
    assignment = {0: 1, 1: 1, 2: 2}
    for node in graph.nodes:
        graph.node_data(node)["boundary_node"] = True
        graph.node_data(node)["area"] = 1
        graph.node_data(node)["boundary_perim"] = 2
    for edge in graph.edges:
        graph.edge_data(edge)["shared_perim"] = 1
    return GeographicPartition(graph, assignment, None, None, None)


def test_geographic_partition_can_be_instantiated(
    example_geographic_partition: GeographicPartition,
):
    partition = example_geographic_partition
    assert isinstance(partition, GeographicPartition)


def test_Partition_parts_is_a_dictionary_of_parts_to_nodes(example_partition: Partition):
    partition = example_partition
    flip = {1: 2}
    new_partition = partition.flip(flip, flips_passed_in_use_original_nx_node_ids=True)
    assert all(isinstance(nodes, frozenset) for nodes in new_partition.parts.values())
    assert all(isinstance(nodes, frozenset) for nodes in partition.parts.values())


def test_Partition_has_subgraphs(example_partition: Partition):
    # Test that subgraphs work as intended.
    # The partition has two parts (districts) with IDs: 1, 2
    # Part #1 has nodes 0, 1, so the subgraph for part #1 should have these nodes
    # Part #2 has node 2, so the subgraph for part #1 should have this node

    # Note that the original node_ids are based on the original NX-based graph
    # The node_ids in the partition's graph have been changed by the conversion
    # from NX to RX, so we need to be careful about when to use "original" node_ids
    # and when to use "internal" RX-based node_ids

    partition = example_partition

    subgraph_for_part_1 = partition.subgraphs[1]
    internal_node_id_0 = subgraph_for_part_1.internal_node_id_for_original_nx_node_id(0)
    internal_node_id_1 = subgraph_for_part_1.internal_node_id_for_original_nx_node_id(1)
    assert set(partition.subgraphs[1].nodes) == {internal_node_id_0, internal_node_id_1}

    subgraph_for_part_2 = partition.subgraphs[2]
    internal_node_id = subgraph_for_part_2.internal_node_id_for_original_nx_node_id(2)
    assert set(partition.subgraphs[2].nodes) == {internal_node_id}
    assert len(list(partition.subgraphs)) == 2


def test_Partition_caches_subgraphs(example_partition: Partition):
    subgraph = example_partition.subgraphs[1]
    assert subgraph is example_partition.subgraphs[1]


def test_partition_implements_getattr_for_updater_access(example_partition: Partition):
    assert example_partition["cut_edges"]


def test_can_be_created_from_a_districtr_file(graph: Graph, districtr_plan_file: pathlib.Path):
    for node in graph:
        graph.node_data(node)["area_num_1"] = node

    # frm: TODO: Testing:  NX vs. RX node_id issues here...

    partition = Partition.from_districtr_file(graph, districtr_plan_file)

    # Convert internal node_ids of the partition's graph to "original" node_ids
    internal_node_assignment = partition.assignment.to_dict()
    original_node_assignment = {}
    for internal_node_id, part in internal_node_assignment.items():
        original_nx_node_id = partition.graph.original_nx_node_id_for_internal_node_id(
            internal_node_id
        )
        original_node_assignment[original_nx_node_id] = part

    assert original_node_assignment == {
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


def test_from_districtr_plan_raises_if_id_column_missing(
    graph: Graph, districtr_plan_file: pathlib.Path
):
    with pytest.raises(TypeError):
        Partition.from_districtr_file(graph, districtr_plan_file)


@pytest.fixture
def districtr_plan_file() -> Iterator[pathlib.Path]:
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


def test_repr(example_partition: Partition):
    assert repr(example_partition) == "<Partition [2 parts]>"


def test_partition_has_default_updaters(example_partition: Partition):
    partition = example_partition
    should_have_updaters = {"cut_edges": cut_edges}

    for updater in should_have_updaters:
        assert should_have_updaters[updater](partition) == partition[updater]


def test_partition_does_not_mutate_default_updaters(graph: Graph):
    custom_updater = "custom_for_default_isolation_test"
    Partition(
        graph,
        {node: cast(int, node) // 3 for node in graph},
        {custom_updater: lambda partition: partition},
    )

    assert custom_updater not in Partition.default_updaters


def test_partition_has_keys(example_partition: Partition):
    assert "cut_edges" in set(example_partition.keys())


def test_geographic_partition_has_keys(example_geographic_partition: GeographicPartition):
    keys = set(example_geographic_partition.updaters.keys())

    assert "perimeter" in keys
    assert "exterior_boundaries" in keys
    assert "interior_boundaries" in keys
    assert "boundary_nodes" in keys
    assert "cut_edges" in keys
    assert "area" in keys
    assert "cut_edges_by_part" in keys


def test_geographic_partition_has_default_updaters(
    example_geographic_partition: GeographicPartition,
):
    assert example_geographic_partition["perimeter"]
    assert example_geographic_partition["exterior_boundaries"]
    assert example_geographic_partition["interior_boundaries"]
    assert example_geographic_partition["boundary_nodes"]
    assert example_geographic_partition["cut_edges"]
    assert example_geographic_partition["area"]
    assert example_geographic_partition["cut_edges_by_part"]
