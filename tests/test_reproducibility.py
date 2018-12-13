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
        {2: 2},
        {4: 2},
        {1: 2},
        {0: 2},
        {0: 1},
        {1: 1},
        {4: 1},
        {6: 1},
        {2: 1},
        {7: 1},
        {8: 1},
        {2: 2},
        {5: 1},
        {1: 2},
        {1: 1},
        {1: 2},
        {5: 2},
        {1: 1},
        {4: 2},
    ]
    flips = [partition.flips for partition in chain]
    print(flips)
    assert flips == expected_flips
