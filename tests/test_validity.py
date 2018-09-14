from unittest.mock import MagicMock

import networkx as nx
import pytest

from rundmcmc.validity import (Validator, contiguous, districts_within_tolerance,
                               fast_connected, single_flip_contiguous, SelfConfiguringLowerBound,
                               no_vanishing_districts)


class MockContiguousPartition:
    def __init__(self):
        graph = nx.Graph()
        graph.add_nodes_from(range(4))
        graph.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0)])
        self.graph = graph
        self.assignment = {0: 0, 1: 1, 2: 1, 3: 0}
        self.flips = None
        self.parent = None

        # This flip will maintain contiguity.
        self.test_flips = {0: 1}


class MockDiscontiguousPartition:
    def __init__(self):
        graph = nx.Graph()
        graph.add_nodes_from(range(4))
        graph.add_edges_from([(0, 1), (1, 2), (2, 3)])
        self.graph = graph
        self.assignment = {0: 0, 1: 1, 2: 1, 3: 0}
        self.flips = None
        self.parent = None

        # This flip will maintain discontiguity.
        self.test_flips = {1: 0}


def test_contiguous_with_contiguity_no_flips_is_true():
    contiguous_partition = MockContiguousPartition()
    assert contiguous(contiguous_partition)
    assert single_flip_contiguous(contiguous_partition)
    assert fast_connected(contiguous_partition)


def test_contiguous_with_contiguity_flips_is_true():
    contiguous_partition = MockContiguousPartition()
    contiguous_partition.flips = contiguous_partition.test_flips
    assert contiguous(contiguous_partition)
    assert single_flip_contiguous(contiguous_partition)
    assert fast_connected(contiguous_partition)


def test_discontiguous_with_contiguity_no_flips_is_false():
    discontiguous_partition = MockDiscontiguousPartition()
    assert not contiguous(discontiguous_partition)
    assert not single_flip_contiguous(discontiguous_partition)
    assert not fast_connected(discontiguous_partition)


def test_discontiguous_with_contiguity_flips_is_false():
    discontiguous_partition = MockDiscontiguousPartition()
    discontiguous_partition.flips = discontiguous_partition.test_flips
    assert not contiguous(discontiguous_partition)
    assert not single_flip_contiguous(discontiguous_partition)
    assert not fast_connected(discontiguous_partition)


def test_districts_within_tolerance_returns_false_if_districts_are_not_within_tolerance():
    # 100 and 1 are not within 1% of each other, so we should expect False
    mock_partition = {'population': {0: 100.0, 1: 1.0}}

    result = districts_within_tolerance(
        mock_partition, attribute_name='population', percentage=0.01)

    assert result is False


def test_districts_within_tolerance_returns_true_if_districts_are_within_tolerance():
    # 100 and 100.1 are not within 1% of each other, so we should expect True
    mock_partition = {'population': {0: 100.0, 1: 100.1}}

    result = districts_within_tolerance(
        mock_partition, attribute_name='population', percentage=0.01)

    assert result is True


def test_self_configuring_lower_bound_always_allows_the_first_argument_it_gets():
    mock_partition = {'value': 1}

    def mock_func(partition):
        return partition['value']

    bound = SelfConfiguringLowerBound(mock_func)
    assert bound(mock_partition)
    assert bound(mock_partition)
    assert bound(mock_partition)


def test_validator_raises_TypeError_if_constraint_returns_non_boolean():
    def function():
        pass

    mock_partition = MagicMock()

    mock_constraint = MagicMock()
    mock_constraint.return_value = function
    mock_constraint.__name__ = "mock_constraint"

    validator = Validator([mock_constraint])

    with pytest.raises(TypeError):
        validator(mock_partition)


def test_no_vanishing_districts_works():
    parent = MagicMock()
    parent.assignment = {1: 1, 2: 2}
    partition = MagicMock()
    partition.parent = parent
    partition.assignment = {1: 2, 2: 2}

    assert not no_vanishing_districts(partition)
