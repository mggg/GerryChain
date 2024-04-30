import os
import pytest
import random

random.seed(2018)


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


@pytest.mark.slow
def test_pa_freeze():
    from gerrychain import (
        GeographicPartition,
        Graph,
        MarkovChain,
        proposals,
        updaters,
        constraints,
        accept,
    )
    import hashlib
    from gerrychain.proposals import recom
    from functools import partial

    random.seed(2018)

    graph = Graph.from_json("docs/_static/PA_VTDs.json")

    my_updaters = {"population": updaters.Tally("TOT_POP", alias="population")}
    initial_partition = GeographicPartition(
        graph, assignment="2011_PLA_1", updaters=my_updaters
    )

    ideal_population = sum(initial_partition["population"].values()) / len(
        initial_partition
    )

    # We use functools.partial to bind the extra parameters (pop_col, pop_target, epsilon, node_repeats)
    # of the recom proposal.
    proposal = partial(
        recom,
        pop_col="TOT_POP",
        pop_target=ideal_population,
        epsilon=0.02,
        node_repeats=2,
    )

    pop_constraint = constraints.within_percent_of_ideal_population(
        initial_partition, 0.02
    )

    chain = MarkovChain(
        proposal=proposal,
        constraints=[pop_constraint],
        accept=accept.always_accept,
        initial_state=initial_partition,
        total_steps=100,
    )

    result = ""
    for count, partition in enumerate(chain):
        result += str(list(sorted(partition.population.values())))
        result += str(len(partition.cut_edges))
        result += str(count) + "\n"

    # This needs to be changed every time we change the
    # tests around
    assert (
        hashlib.sha256(result.encode()).hexdigest()
        == "aa7a5f7116c7b10b7857aeb3555fd88d8dfc5d810dc0b706f8772efba3c78607"
    )
