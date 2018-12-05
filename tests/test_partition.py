import networkx
import pytest

from gerrychain.partition import GeographicPartition, Partition
from gerrychain.proposals import propose_random_flip
from gerrychain.updaters import cut_edges


@pytest.fixture
def example_partition():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}
    partition = Partition(graph, assignment, {"cut_edges": cut_edges})
    return partition


def test_Partition_can_be_flipped(example_partition):
    flip = {1: 2}
    new_partition = example_partition.merge(flip)
    assert new_partition.assignment[1] == 2


def test_Partition_knows_cut_edges_K3(example_partition):
    partition = example_partition
    assert (1, 2) in partition['cut_edges'] or (2, 1) in partition['cut_edges']
    assert (0, 2) in partition['cut_edges'] or (2, 0) in partition['cut_edges']


def test_propose_random_flip_proposes_a_dict(example_partition):
    partition = example_partition
    proposal = propose_random_flip(partition)
    assert isinstance(proposal, dict)


@pytest.fixture
def example_geographic_partition():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}
    for node in graph.nodes:
        graph.node[node]['boundary_node'] = False
        graph.node[node]['area'] = 1
    for edge in graph.edges:
        graph.edges[edge]['shared_perim'] = 1
    return GeographicPartition(graph, assignment, None, None, None)


def test_geographic_partition_can_be_instantiated(example_geographic_partition):
    partition = example_geographic_partition
    assert partition.updaters == GeographicPartition.default_updaters


def test_Partition_parts_is_just_the_tuple_of_ids():
    partition = example_partition()
    flip = {1: 2}
    new_partition = partition.merge(flip)
    assert new_partition.parts == partition.parts == (1, 2)
