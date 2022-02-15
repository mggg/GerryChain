from unittest.mock import MagicMock

import networkx as nx
import numpy
import pytest

from gerrychain.constraints import (SelfConfiguringLowerBound, Validator,
                                    contiguous, contiguous_bfs,
                                    districts_within_tolerance,
                                    no_vanishing_districts,
                                    single_flip_contiguous)
from gerrychain.partition import Partition
from gerrychain.partition.partition import get_assignment
from gerrychain.graph import Graph


@pytest.fixture
def contiguous_partition_with_flips():
    graph = nx.Graph()
    graph.add_nodes_from(range(4))
    graph.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0)])
    partition = Partition(Graph.from_networkx(graph), {0: 0, 1: 1, 2: 1, 3: 0})

    # This flip will maintain contiguity.
    return partition, {0: 1}


@pytest.fixture
def discontiguous_partition_with_flips():
    graph = nx.Graph()
    graph.add_nodes_from(range(4))
    graph.add_edges_from([(0, 1), (1, 2), (2, 3)])
    partition = Partition(Graph.from_networkx(graph), {0: 0, 1: 1, 2: 1, 3: 0})

    # This flip will maintain discontiguity.
    return partition, {1: 0}


@pytest.fixture
def contiguous_partition(contiguous_partition_with_flips):
    return contiguous_partition_with_flips[0]


@pytest.fixture
def discontiguous_partition(discontiguous_partition_with_flips):
    return discontiguous_partition_with_flips[0]


def test_contiguous_with_contiguity_no_flips_is_true(contiguous_partition):
    assert contiguous(contiguous_partition)
    assert single_flip_contiguous(contiguous_partition)
    assert contiguous_bfs(contiguous_partition)


def test_contiguous_with_contiguity_flips_is_true(contiguous_partition_with_flips):
    contiguous_partition, test_flips = contiguous_partition_with_flips
    contiguous_partition2 = contiguous_partition.flip(test_flips)
    assert contiguous(contiguous_partition2)
    assert single_flip_contiguous(contiguous_partition2)
    assert contiguous_bfs(contiguous_partition2)


def test_discontiguous_with_contiguous_no_flips_is_false(discontiguous_partition):
    assert not contiguous(discontiguous_partition)


def test_discontiguous_with_single_flip_contiguous_no_flips_is_false(
    discontiguous_partition
):
    assert not single_flip_contiguous(discontiguous_partition)


def test_discontiguous_with_contiguous_bfs_no_flips_is_false(discontiguous_partition):
    assert not contiguous_bfs(discontiguous_partition)


def test_discontiguous_with_contiguous_flips_is_false(
    discontiguous_partition_with_flips
):
    part, test_flips = discontiguous_partition_with_flips
    discontiguous_partition2 = part.flip(test_flips)
    assert not contiguous(discontiguous_partition2)


@pytest.mark.xfail(
    reason="single_flip_contiguous does not work"
    "when the previous partition is discontiguous"
)
def test_discontiguous_with_single_flip_contiguous_flips_is_false(
    discontiguous_partition_with_flips
):
    part, test_flips = discontiguous_partition_with_flips
    discontiguous_partition2 = part.flip(test_flips)
    assert not single_flip_contiguous(discontiguous_partition2)


def test_discontiguous_with_contiguous_bfs_flips_is_false(
    discontiguous_partition_with_flips
):
    part, test_flips = discontiguous_partition_with_flips
    discontiguous_partition2 = part.flip(test_flips)
    assert not contiguous_bfs(discontiguous_partition2)


def test_districts_within_tolerance_returns_false_if_districts_are_not_within_tolerance():
    # 100 and 1 are not within 1% of each other, so we should expect False
    mock_partition = {"population": {0: 100.0, 1: 1.0}}

    result = districts_within_tolerance(
        mock_partition, attribute_name="population", percentage=0.01
    )

    assert result is False


def test_districts_within_tolerance_returns_true_if_districts_are_within_tolerance():
    # 100 and 100.1 are not within 1% of each other, so we should expect True
    mock_partition = {"population": {0: 100.0, 1: 100.1}}

    result = districts_within_tolerance(
        mock_partition, attribute_name="population", percentage=0.01
    )

    assert result is True


def test_self_configuring_lower_bound_always_allows_the_first_argument_it_gets():
    mock_partition = {"value": 1}

    def mock_func(partition):
        return partition["value"]

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


def test_validator_accepts_numpy_booleans():
    mock_partition = MagicMock()

    mock_constraint = MagicMock()
    mock_constraint.return_value = numpy.bool_(True)
    mock_constraint.__name__ = "mock_constraint"

    is_valid = Validator([mock_constraint])
    assert is_valid(mock_partition)


def test_no_vanishing_districts_works():
    parent = MagicMock()
    parent.assignment = get_assignment({1: 1, 2: 2}, MagicMock())

    partition = MagicMock()
    partition.parent = parent
    partition.assignment = parent.assignment.copy()
    partition.assignment.update_flows({1: {"out": set(), "in": {2}}, 2: {"out": {2}, "in": set()}})

    assert not no_vanishing_districts(partition)
