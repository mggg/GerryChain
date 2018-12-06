import pytest

from gerrychain.partition import Partition
from gerrychain.tree_methods import tree_part2
from gerrychain.updaters import Tally


@pytest.fixture
def graph_with_pop(three_by_three_grid):
    for node in three_by_three_grid:
        three_by_three_grid.nodes[node]["pop"] = 1
    return three_by_three_grid


@pytest.fixture
def partition_with_pop(graph_with_pop):
    return Partition(
        graph_with_pop,
        {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 1, 7: 1, 8: 1},
        updaters={"pop": Tally("pop")},
    )


def test_tree_part2_returns_a_2_partition(partition_with_pop):
    result = tree_part2(
        partition_with_pop, partition_with_pop.graph, "pop", 4.5, 0.25, 10
    )
    print(result)
    assert len(result) == 2
    assert sum(len(nodes) for nodes in result.values()) == len(partition_with_pop.graph)
