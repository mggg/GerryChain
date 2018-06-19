from rundmcmc.validity import contiguous, single_flip_contiguous, fast_connected
import networkx as nx


class MockContiguousPartition:
    def __init__(self):
        graph = nx.Graph()
        graph.add_nodes_from(range(4))
        graph.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0)])
        self.graph = graph
        self.assignment = {0: 0, 1: 1, 2: 1, 3: 0}

        # This flip will maintain contiguity.
        self.test_flips = {0: 1}


class MockDiscontiguousPartition:
    def __init__(self):
        graph = nx.Graph()
        graph.add_nodes_from(range(4))
        graph.add_edges_from([(0, 1), (1, 2), (2, 3)])
        self.graph = graph
        self.assignment = {0: 0, 1: 1, 2: 1, 3: 0}

        # This flip will maintain discontiguity.
        self.test_flips = {1: 0}


def test_contiguous_with_contiguity_no_flips_is_true():
    contiguous_partition = MockContiguousPartition()
    assert contiguous(contiguous_partition)
    assert single_flip_contiguous(contiguous_partition)
    assert fast_connected(contiguous_partition)


def test_contiguous_with_contiguity_flips_is_true():
    contiguous_partition = MockContiguousPartition()
    flips = contiguous_partition.test_flips
    assert contiguous(contiguous_partition, flips)
    assert single_flip_contiguous(contiguous_partition, flips)
    assert fast_connected(contiguous_partition, flips)


def test_discontiguous_with_contiguity_no_flips_is_false():
    discontiguous_partition = MockDiscontiguousPartition()
    assert not contiguous(discontiguous_partition)
    assert not single_flip_contiguous(discontiguous_partition)
    assert not fast_connected(discontiguous_partition)


def test_discontiguous_with_contiguity_flips_is_false():
    discontiguous_partition = MockDiscontiguousPartition()
    flips = discontiguous_partition.test_flips
    assert not contiguous(discontiguous_partition, flips)
    assert not single_flip_contiguous(discontiguous_partition, flips)
    assert not fast_connected(discontiguous_partition, flips)
