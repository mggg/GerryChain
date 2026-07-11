"""Reproducibility tests.

Two guarantees are pinned here:

1. A seeded chain produces the same trajectory regardless of PYTHONHASHSEED. This is checked by
   running the same seeded script in subprocesses with different hash seeds and comparing output
   byte-for-byte, covering every proposal whose draws pass through a set-to-sequence conversion.
2. A fixed seed produces a known trajectory (golden test), so unintentional changes to how the
   RNG stream is consumed get noticed.
"""

import os
import subprocess
import sys

import pytest

# Run in a subprocess so each execution gets its own string-hash seed. String part labels on
# purpose: they exercise the sorted() set-to-sequence conversions in recom and the two
# slow_reversible proposals that used to make chains PYTHONHASHSEED-sensitive.
HASHSEED_SCRIPT = """
from functools import partial

import networkx as nx

from gerrychain import Graph, MarkovChain, Partition
from gerrychain.accept import always_accept
from gerrychain.constraints import contiguous
from gerrychain.proposals import (
    propose_random_flip,
    recom,
    slow_reversible_propose,
    slow_reversible_propose_bi,
)
from gerrychain.updaters import Tally, cut_edges

nx_graph = nx.grid_graph(dim=[5, 4])
nx_graph = nx.convert_node_labels_to_integers(nx_graph)
for node in nx_graph.nodes:
    nx_graph.nodes[node]["population"] = 10


def make_partition():
    graph = Graph.from_networkx(nx_graph)
    assignment = {node: "abcd"[node // 5] for node in range(20)}
    return Partition(
        graph,
        assignment,
        {"population": Tally("population", alias="population"), "cut_edges": cut_edges},
    )


proposals = {
    "flip": propose_random_flip,
    "recom": partial(recom, pop_col="population", pop_target=50, epsilon=0.0, node_repeats=1),
    "slow_reversible": slow_reversible_propose,
    "slow_reversible_bi": slow_reversible_propose_bi,
}

for name, proposal in proposals.items():
    chain = MarkovChain(proposal, [contiguous], always_accept, make_partition(), 15, rng=2018)
    print(name, [sorted(part.assignment.mapping.items()) for part in chain])
"""


def run_with_hashseed(hashseed):
    env = dict(os.environ)
    if hashseed is None:
        env.pop("PYTHONHASHSEED", None)
    else:
        env["PYTHONHASHSEED"] = hashseed
    result = subprocess.run(
        [sys.executable, "-c", HASHSEED_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return result.stdout


def test_trajectories_do_not_depend_on_pythonhashseed():
    baseline = run_with_hashseed("0")
    assert run_with_hashseed("42") == baseline
    assert run_with_hashseed(None) == baseline


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
        {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2},
        {"cut_edges": updaters.cut_edges},
    )
    chain = MarkovChain(
        proposals.propose_random_flip,
        constraints.single_flip_contiguous,
        accept.always_accept,
        partition,
        20,
        rng=2018,
    )
    # Captured with rng=2018. Regenerate (and make sure it passes consistently) whenever a
    # library change alters how the RNG stream is consumed - e.g. before a release.
    expected_flips = [
        None,
        {2: 2},
        {4: 2},
        {0: 2},
        {0: 1},
        {3: 2},
        {1: 2},
        {2: 1},
        {2: 2},
        {2: 1},
        {4: 1},
        {4: 2},
        {6: 1},
        {0: 2},
        {4: 1},
        {7: 1},
        {8: 1},
        {5: 1},
        {3: 1},
        {0: 1},
    ]
    flips = [partition.flips for partition in chain]
    assert flips == expected_flips


@pytest.mark.slow
def test_pa_freeze():
    import hashlib
    from functools import partial

    from gerrychain import (
        GeographicPartition,
        Graph,
        MarkovChain,
        accept,
        constraints,
        updaters,
    )
    from gerrychain.proposals import recom

    graph = Graph.from_json("docs/_static/PA_VTDs.json")

    my_updaters = {"population": updaters.Tally("TOT_POP", alias="population")}
    initial_partition = GeographicPartition(graph, assignment="2011_PLA_1", updaters=my_updaters)

    ideal_population = sum(initial_partition["population"].values()) / len(initial_partition)

    # We use functools.partial to bind the extra parameters (pop_col, pop_target, epsilon, node_repeats)
    # of the recom proposal.
    proposal = partial(
        recom,
        pop_col="TOT_POP",
        pop_target=ideal_population,
        epsilon=0.02,
        node_repeats=2,
    )

    pop_constraint = constraints.within_percent_of_ideal_population(initial_partition, 0.02)

    chain = MarkovChain(
        proposal=proposal,
        constraints=[pop_constraint],
        accept=accept.always_accept,
        initial_state=initial_partition,
        total_steps=100,
        rng=2018,
    )

    result = ""
    for count, partition in enumerate(chain):
        result += str(list(sorted(partition["population"].values())))
        result += str(len(partition["cut_edges"]))
        result += str(count) + "\n"

    # This needs to be changed every time we change the
    # tests around. Captured with rng=2018; independent of PYTHONHASHSEED.
    assert (
        hashlib.sha256(result.encode()).hexdigest()
        == "5b664f32331c5afe07b5170ab893078427342ec586e8fd2ef6d873bddd6e3cfc"
    )
