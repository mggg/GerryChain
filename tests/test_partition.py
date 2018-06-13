from rundmcmc.partition import Partition, propose_random_flip
import networkx


def example_partition():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}
    partition = Partition(graph, assignment)
    return partition


def test_Partition_can_be_flipped():
    partition = example_partition()
    flip = {1: 2}
    new_partition = partition.merge(flip)
    assert new_partition.assignment[1] == 2


def test_Partition_knows_cut_edges_K3():
    partition = example_partition()
    assert (1, 2) in partition.cut_edges or (2, 1) in partition.cut_edges
    assert (0, 2) in partition.cut_edges or (2, 0) in partition.cut_edges


def test_propose_random_flip_proposes_a_dict():
    partition = example_partition()
    proposal = propose_random_flip(partition)
    assert isinstance(proposal, dict)


def test_Partition_can_update_stats():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}

    graph.nodes[0]['stat'] = 1
    graph.nodes[1]['stat'] = 2
    graph.nodes[2]['stat'] = 3

    partition = Partition(graph, assignment, aggregate_fields=['stat'])
    assert partition.statistics['stat'][2] == 3
    flip = {1: 2}

    new_partition = partition.merge(flip)
    assert new_partition.statistics['stat'][2] == 5
