import pytest

from gerrychain import Partition
from gerrychain.updaters.locality_split_scores import LocalitySplits
from gerrychain.updaters.cut_edges import cut_edges
from gerrychain import Graph

@pytest.fixture
def three_by_three_grid():
    """Returns a graph that looks like this:
    0 1 2
    3 4 5
    6 7 8
    """
    graph = Graph()
    graph.add_edges_from(
        [
            (0, 1),
            (0, 3),
            (1, 2),
            (1, 4),
            (2, 5),
            (3, 4),
            (3, 6),
            (4, 5),
            (4, 7),
            (5, 8),
            (6, 7),
            (7, 8),
        ]
    )
    return graph


@pytest.fixture
def graph_with_counties(three_by_three_grid):
    for node in [0, 1, 2]:
        three_by_three_grid.nodes[node]["county"] = "a"
        three_by_three_grid.nodes[node]["pop"] = 1
    for node in [3, 4, 5]:
        three_by_three_grid.nodes[node]["county"] = "b"
        three_by_three_grid.nodes[node]["pop"] = 1
    for node in [6, 7, 8]:
        three_by_three_grid.nodes[node]["county"] = "c"
        three_by_three_grid.nodes[node]["pop"] = 1
    return three_by_three_grid


@pytest.fixture
def partition(graph_with_counties):
    partition = Partition(
        graph_with_counties,
        assignment={0: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3},
        updaters={"cut_edges":cut_edges, "splits": LocalitySplits("splittings", "county", "pop", ['num_parts', 'num_pieces',
            'naked_boundary', 'shannon_entropy', 'power_entropy',
            'symmetric_entropy', 'num_split_localities'])},
    )
    return partition


@pytest.fixture
def split_partition(graph_with_counties):
    partition = Partition(
        graph_with_counties,
        assignment={0: 1, 1: 2, 2: 3, 3: 1, 4: 2, 5: 3, 6: 1, 7: 2, 8: 3},
        updaters={"cut_edges":cut_edges, "splits": LocalitySplits("splittings", "county", "pop", ['num_parts', 'num_pieces',
            'naked_boundary', 'shannon_entropy', 'power_entropy',
            'symmetric_entropy', 'num_split_localities'])},
    )
    return partition






class TestSplittingScores:
	
    
    def test_not_split(self, partition):
        part = partition.updaters["splits"](partition)
        result = partition.updaters["splits"].scores

        assert result["num_parts"] == 3
        assert result["num_pieces"] == 3
        assert result["naked_boundary"] == 0
        assert result["shannon_entropy"] == 0
        assert result["power_entropy"] == 0
        assert result["symmetric_entropy"] == 18
        assert result["num_split_localities"] == 0

    def test_is_split(self, split_partition):
        part = split_partition.updaters["splits"](split_partition)
        result = split_partition.updaters["splits"].scores

        assert result["num_parts"] == 9
        assert result["num_pieces"] == 9
        assert result["naked_boundary"] == 6
        assert 1.2 > result["shannon_entropy"] > 1
        assert .6 > result["power_entropy"] > .5
        assert 32 > result["symmetric_entropy"] > 31 
        assert result["num_split_localities"] == 3





