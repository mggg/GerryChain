from collections.abc import Mapping
from typing import Any, cast

import pandas
import pytest

from gerrychain.partition.assignment import Assignment, get_assignment


@pytest.fixture
def assignment() -> Assignment:
    return Assignment.from_dict({1: 1, 2: 2, 3: 2})


class TestAssignment:
    def test_assignment_can_be_updated(self, assignment: Assignment):
        assignment.update_flows({1: {"out": set(), "in": {2}}, 2: {"out": {2}, "in": set()}})
        assert assignment[2] == 1

    def test_assignment_copy_does_not_copy_the_node_sets(self, assignment: Assignment):
        assignment2 = assignment.copy()
        for part in assignment.parts:
            assert assignment2[part] is assignment[part]

    def test_to_series(self, assignment: Assignment):
        series = assignment.to_series()

        assert isinstance(series, pandas.Series)
        assert list(series.items()) == [(1, 1), (2, 2), (3, 2)]

    def test_to_vector(self):
        assignment = Assignment.from_dict({0: 1, 1: 1, 2: 2})
        assert assignment.to_vector().tolist() == [1, 1, 2]

    def test_to_vector_requires_contiguous_0_based_node_ids(self, assignment: Assignment):
        # The fixture's nodes are {1, 2, 3}, which are not 0-based.
        with pytest.raises(ValueError, match="contiguous"):
            assignment.to_vector()

    def test_to_vector_ignores_mapping_insertion_order(self):
        assignment = Assignment.from_dict({2: "c", 0: "a", 1: "b"})
        assert assignment.to_vector().tolist() == ["a", "b", "c"]

    def test_to_vector_rejects_gap_in_node_ids(self):
        # Keys {0, 2} have the right length for range(2) but a hole at 1.
        assignment = Assignment.from_dict({0: "a", 2: "b"})
        with pytest.raises(ValueError, match="contiguous"):
            assignment.to_vector()

    def test_to_vector_string_labels_are_not_width_limited(self):
        assignment = Assignment.from_dict({0: "a", 1: "b"})
        vector = assignment.to_vector().copy()
        vector[0] = "a_label_longer_than_one_character"
        assert vector[0] == "a_label_longer_than_one_character"

    def test_to_dict(self, assignment: Assignment):
        assignment_dict = assignment.to_dict()

        assert isinstance(assignment_dict, dict)
        assert list(assignment_dict.items()) == [(1, 1), (2, 2), (3, 2)]

    def test_has_get_method_like_a_dict(self, assignment: Assignment):
        assert assignment.get(1) == 1
        # Mapping.get is positional-only in typeshed, but the runtime ABC takes a keyword.
        assert cast(Any, assignment).get("not a node", default=5) == 5

    def test_raises_keyerror_for_missing_nodes(self, assignment: Assignment):
        with pytest.raises(KeyError):
            assignment["not a node"]

    def test_can_update_parts(self, assignment: Assignment):
        assignment.update_parts({2: {2}, 3: {3}})
        assert assignment.to_dict() == {1: 1, 2: 2, 3: 3}

    def test_implements_Mapping_abc(self, assignment: Assignment):
        # __iter__
        assert list(assignment) == [1, 2, 3]

        # __contains__
        for i in [1, 2, 3]:
            assert i in assignment

        # __len__
        assert len(assignment) == 3

        # __getitem__
        assert assignment[1] == 1
        assert assignment[3] == 2

        # keys()
        keys = list(assignment.keys())
        assert len(keys) == 3
        assert set(keys) == {1, 2, 3}

        # values()
        values = list(assignment.values())
        assert len(values) == 3
        assert set(values) == {1, 2}

        # items()
        items = list(assignment.items())
        assert len(items) == 3
        assert set(items) == {(1, 1), (2, 2), (3, 2)}

        # __eq__
        assert assignment == {1: 1, 2: 2, 3: 2}

        assert isinstance(assignment, Mapping)

    def test_assignment_raises_if_a_key_has_two_assignments(self):
        with pytest.raises(ValueError):
            Assignment({"one": frozenset({1, 2, 3}), "two": frozenset({1, 4, 5})})

    def test_assignment_can_be_instantiated_from_series(self):
        series = pandas.Series([1, 2, 1, 2], index=[1, 2, 3, 4])
        assignment = Assignment.from_dict(series)
        assert assignment == {1: 1, 2: 2, 3: 1, 4: 2}


def test_get_assignment_accepts_assignment(assignment: Assignment):
    created = assignment
    get_assignment(assignment)
    assert assignment is created


def test_get_assignment_raises_typeerror_for_unexpected_input():
    with pytest.raises(TypeError):
        get_assignment(cast(str, None))


def test_get_assignment_with_series():
    series = pandas.Series([1, 2, 1, 2], index=[1, 2, 3, 4])
    assignment = get_assignment(series)
    assert isinstance(assignment, Assignment)
    assert assignment == {1: 1, 2: 2, 3: 1, 4: 2}


def test_repr(assignment: Assignment):
    assert repr(assignment) == "<Assignment [3 keys, 2 parts]>"
