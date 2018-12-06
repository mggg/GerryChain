import pytest

from gerrychain.partition.assignment import Assignment


@pytest.fixture
def assignment():
    return Assignment.from_dict({1: 1, 2: 2, 3: 2})


def test_assignment_can_be_updated(assignment):
    assignment.update({2: 1})
    assert assignment[2] == 1


def test_assignment_copy_does_not_copy_the_node_sets(assignment):
    assignment2 = assignment.copy()
    for part in assignment.parts:
        assert assignment2[part] is assignment[part]
