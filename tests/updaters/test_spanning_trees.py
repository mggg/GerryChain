from gerrychain import Partition
from gerrychain.updaters import num_spanning_trees


def test_get_num_spanning_trees(three_by_three_grid):
    assignment = {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1}
    partition = Partition(
        three_by_three_grid,
        assignment,
        {"num_spanning_trees": num_spanning_trees}
    )
    assert 192 == round(partition["num_spanning_trees"][1])
    assert [1] == list(partition["num_spanning_trees"].keys())
