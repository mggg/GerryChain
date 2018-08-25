import networkx
import pytest

from rundmcmc.partition import Partition
from rundmcmc.proposals import propose_random_flip


@pytest.fixture
def example_partition():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}
    partition = Partition(graph, assignment)
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


def test_Partition_keeps_track_of_parts(example_partition):
    partition = example_partition
    flip = {1: 2}
    new_partition = partition.merge(flip)
    assert new_partition.parts[2] == {1, 2} and new_partition.parts[1] == {0}


def test_Partition_does_not_mutate_parent(example_partition):
    partition = example_partition
    flip = {1: 2}
    new_partition = partition.merge(flip)
    # the parts dict should not be shared
    assert partition.parts is not new_partition.parts
    # the old partition's parts should be preserved

    assert partition.parts[1] == {0, 1} and partition.parts[2] == {2}


def test_partition_can_create_new_parts_in_flips(example_partition):
    partition = example_partition
    # Assign 1 to a part that doesn't exist in partition (99)
    flip = {1: 99}
    new_partition = partition.merge(flip)
    assert 1 in new_partition.parts[99]


def test_partition_has_no_empty_parts(example_partition):
    partition = example_partition

    flips = {node: 99 for node in partition.graph.nodes}
    new_partition = partition.merge(flips)
    parts = new_partition.parts

    assert all(len(parts[part]) > 0 for part in parts)
