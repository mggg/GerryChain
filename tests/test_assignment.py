from gerrychain.partition.partition import Assignment


def test_assignment_can_be_updated():
    assignment = Assignment.from_dict({1: 1, 2: 2, 3: 2})
    assignment.update({2: 1})
    assert assignment[2] == 1
