import pytest

from gerrychain import Partition
from gerrychain.updaters.county_splits import (CountySplit,
                                               compute_county_splits,
                                               county_splits)


@pytest.fixture
def graph_with_counties(three_by_three_grid):
    for node in [0, 1, 2]:
        three_by_three_grid.nodes[node]["county"] = "a"
    for node in [3, 4, 5]:
        three_by_three_grid.nodes[node]["county"] = "b"
    for node in [6, 7, 8]:
        three_by_three_grid.nodes[node]["county"] = "c"
    return three_by_three_grid


@pytest.fixture
def partition(graph_with_counties):
    partition = Partition(
        graph_with_counties,
        assignment={0: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3},
        updaters={"splits": county_splits("splits", "county")},
    )
    return partition


@pytest.fixture
def split_partition(graph_with_counties):
    partition = Partition(
        graph_with_counties,
        assignment={0: 1, 1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3},
        updaters={"splits": county_splits("splits", "county")},
    )
    return partition


class TestComputeCountySplits:
    def test_describes_splits_for_all_counties(self, partition):
        result = partition["splits"]

        assert set(result.keys()) == {"a", "b", "c"}

        after_a_flip = partition.flip({3: 1})
        second_result = after_a_flip["splits"]

        assert set(second_result.keys()) == {"a", "b", "c"}

    def test_no_splits(self, graph_with_counties):
        partition = Partition(graph_with_counties, assignment="county")

        result = compute_county_splits(partition, "county", None)

        for splits_info in result.values():
            assert splits_info.split == CountySplit.NOT_SPLIT

    def test_new_split(self, partition):
        after_a_flip = partition.flip({3: 1})
        result = after_a_flip["splits"]

        # County b is now split, but a and c are not
        assert result["a"].split == CountySplit.NOT_SPLIT
        assert result["b"].split == CountySplit.NEW_SPLIT
        assert result["c"].split == CountySplit.NOT_SPLIT

    def test_initial_split(self, split_partition):
        result = split_partition["splits"]

        # County b starts out split, but a and c are not
        assert result["a"].split == CountySplit.NOT_SPLIT
        assert result["b"].split == CountySplit.OLD_SPLIT
        assert result["c"].split == CountySplit.NOT_SPLIT

    def test_old_split(self, split_partition):
        after_a_flip = split_partition.flip({4: 1})
        result = after_a_flip["splits"]

        # County b becomes more split
        assert result["a"].split == CountySplit.NOT_SPLIT
        assert result["b"].split == CountySplit.OLD_SPLIT
        assert result["c"].split == CountySplit.NOT_SPLIT

    @pytest.mark.xfail(
        reason="county_splits only remembers the splits from the "
        "previous partition, which is not the intuitive behavior."
    )
    def test_initial_split_that_disappears_and_comes_back(self, split_partition):
        no_splits = split_partition.flip({3: 2})
        result = no_splits["splits"]
        assert all(info.split == CountySplit.NOT_SPLIT for info in result.values())

        split_comes_back = no_splits.flip({3: 1})
        new_result = split_comes_back["splits"]
        assert new_result["a"].split == CountySplit.NOT_SPLIT
        assert new_result["b"].split == CountySplit.OLD_SPLIT
        assert new_result["c"].split == CountySplit.NOT_SPLIT
