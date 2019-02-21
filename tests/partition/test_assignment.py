import pandas
import pytest

from gerrychain.partition.assignment import Assignment


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
