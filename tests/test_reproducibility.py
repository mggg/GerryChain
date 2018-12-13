import pytest


@pytest.mark.xfail(reason="Setting random.seed is not sufficient")
def test_repeatable(three_by_three_grid):
    from gerrychain import (
        MarkovChain,
        Partition,
        accept,
        constraints,
        proposals,
        updaters,
    )

    partition = Partition(
        three_by_three_grid,
        {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2, 9: 2},
        {"cut_edges": updaters.cut_edges},
    )
    chain = MarkovChain(
        proposals.propose_random_flip,
        constraints.single_flip_contiguous,
        accept.always_accept,
        partition,
        20,
    )
    # Note: these might not even be the actual expected flips
    expected_flips = [
        None,
        {5: 1},
        {3: 2},
        {3: 1},
        {3: 2},
        {3: 1},
        {6: 1},
        {8: 1},
        {8: 2},
        {6: 2},
        {4: 2},
        {4: 1},
        {5: 2},
        {4: 2},
        {4: 1},
        {3: 2},
        {4: 2},
        {0: 2},
        {1: 2},
        {5: 1},
    ]
    flips = [partition.flips for partition in chain]
    print(flips)
    assert flips == expected_flips
