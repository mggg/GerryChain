import pandas
import pytest

from gerrychain.partition.assignment import Assignment, get_assignment
from collections.abc import Mapping


@pytest.fixture
def assignment():
    return Assignment.from_dict({1: 1, 2: 2, 3: 2})


class TestAssignment:
    def test_assignment_can_be_updated(self, assignment):
        assignment.update({2: 1})
        assert assignment[2] == 1

    def test_assignment_copy_does_not_copy_the_node_sets(self, assignment):
        assignment2 = assignment.copy()
        for part in assignment.parts:
            assert assignment2[part] is assignment[part]

    def test_to_series(self, assignment):
        series = assignment.to_series()

        assert isinstance(series, pandas.Series)
        assert list(series.items()) == [(1, 1), (2, 2), (3, 2)]

    def test_to_dict(self, assignment):
        assignment_dict = assignment.to_dict()

        assert isinstance(assignment_dict, dict)
        assert list(assignment_dict.items()) == [(1, 1), (2, 2), (3, 2)]

    def test_has_get_method_like_a_dict(self, assignment):
        assert assignment.get(1) == 1
        assert assignment.get("not a node", default=5) == 5

    def test_raises_keyerror_for_missing_nodes(self, assignment):
        with pytest.raises(KeyError):
            assignment["not a node"]

    def test_can_update_parts(self, assignment):
        assignment.update_parts({2: {2}, 3: {3}})
        assert assignment.to_dict() == {1: 1, 2: 2, 3: 3}

    def test_implements_Mapping_abc(self, assignment):
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
            Assignment({"one": {1, 2, 3}, "two": {1, 4, 5}})

    def test_assignment_can_be_instantiated_from_series(self):
        series = pandas.Series([1, 2, 1, 2], index=[1, 2, 3, 4])
        assignment = Assignment.from_dict(series)
        assert assignment == {1: 1, 2: 2, 3: 1, 4: 2}


def test_get_assignment_accepts_assignment(assignment):
    created = assignment
    get_assignment(assignment)
    assert assignment is created


def test_get_assignment_raises_typeerror_for_unexpected_input():
    with pytest.raises(TypeError):
        get_assignment(None)


def test_get_assignment_with_series():
    series = pandas.Series([1, 2, 1, 2], index=[1, 2, 3, 4])
    assignment = get_assignment(series)
    assert isinstance(assignment, Assignment)
    assert assignment == {1: 1, 2: 2, 3: 1, 4: 2}


def test_repr(assignment):
    assert repr(assignment) == "<Assignment [3 keys, 2 parts]>"
