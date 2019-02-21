import os

import pytest


@pytest.mark.skipif(
    True or os.environ.get("PYTHONHASHSEED", 1) != "0",
    reason="Need to fix the PYTHONHASHSEED for reproducibility. The expected flips "
    "for this test will change as we make changes to the library, so we only need "
    "to update it and make sure it consistently passes when we are about to make "
    "a new release.",
)
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
        {6: 1},
        {1: 2},
        {7: 1},
        {0: 2},
        {3: 2},
        {7: 2},
        {3: 1},
        {4: 1},
        {7: 1},
        {8: 1},
        {8: 2},
        {8: 1},
        {8: 2},
        {3: 2},
        {4: 2},
        {7: 2},
        {3: 1},
    ]
    flips = [partition.flips for partition in chain]
    print(flips)
    assert flips == expected_flips
