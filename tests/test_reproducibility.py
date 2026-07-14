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
from gerrychain.tree import random_spanning_tree, uniform_spanning_tree
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
    "recom": partial(recom, pop_col="population", pop_target=50, epsilon=0.0),
    "slow_reversible": slow_reversible_propose,
    "slow_reversible_bi": slow_reversible_propose_bi,
}

for name, proposal in proposals.items():
    chain = MarkovChain(proposal, [contiguous], always_accept, make_partition(), 15, rng=2018)
    print(name, [sorted(part.assignment.mapping.items()) for part in chain])


node_order = ["node-7", "node-2", "node-10", "node-0", "node-5", "node-1"]
edges = [
    ("node-7", "node-2"),
    ("node-2", "node-10"),
    ("node-10", "node-0"),
    ("node-0", "node-5"),
    ("node-5", "node-1"),
    ("node-1", "node-7"),
    ("node-2", "node-5"),
]
string_graph = nx.Graph()
string_graph.add_nodes_from((node, {"population": 1}) for node in node_order)
string_graph.add_edges_from(edges)


def normalized_edges(tree):
    return sorted(tuple(sorted(edge)) for edge in tree.edges)


print("nodes", Graph.from_networkx(string_graph.copy()).nodes)
print(
    "initial",
    sorted(
        Partition.from_random_assignment(
            Graph.from_networkx(string_graph.copy()),
            n_parts=2,
            epsilon=0,
            pop_col="population",
            rng=2024,
        ).assignment.mapping.items()
    ),
)
print(
    "random_tree",
    normalized_edges(random_spanning_tree(Graph.from_networkx(string_graph.copy()), rng=2024)),
)
print(
    "uniform_tree",
    normalized_edges(uniform_spanning_tree(Graph.from_networkx(string_graph.copy()), rng=2024)),
)

# Regression for the small subgraph issue: NX subgraph views enumerate their nodes in set
# (hash-dependent) order once the subgraph is smaller than half its parent, which made
# from_random_assignment PYTHONHASHSEED-sensitive on string-node-id graphs. Five parts so that
# recursive_tree_part's remaining-nodes subgraph drops below half the graph (the 2-part
# string_graph case above never crosses that threshold).
grid = nx.grid_graph(dim=[10, 10])
grid = nx.relabel_nodes(grid, {node: f"{node[0]:02d}-{node[1]:02d}" for node in grid})
for node in grid:
    grid.nodes[node]["population"] = 1

print(
    "shrinking_subgraph",
    sorted(
        Partition.from_random_assignment(
            Graph.from_networkx(grid),
            n_parts=5,
            epsilon=0.05,
            pop_col="population",
            rng=2024,
        ).assignment.mapping.items()
    ),
)
"""

RANDOM_ASSIGNMENT_HASHSEED_SCRIPT = """
import hashlib
import json

from gerrychain import Graph, Partition

graph = Graph.from_json("docs/_static/05_bg_census_consolidated.json")
partition = Partition.from_random_assignment(
    graph,
    n_parts=35,
    epsilon=0.02,
    pop_col="tot_pop_20",
    rng=2024,
)
assignment = sorted(partition.assignment.mapping.items())
print(hashlib.sha256(json.dumps(assignment).encode()).hexdigest())
"""


def run_with_hashseed(hashseed, script=HASHSEED_SCRIPT):
    env = dict(os.environ)
    if hashseed is None:
        env.pop("PYTHONHASHSEED", None)
    else:
        env["PYTHONHASHSEED"] = hashseed
    result = subprocess.run(
        [sys.executable, "-c", script],
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


def test_random_assignment_does_not_depend_on_pythonhashseed():
    baseline = run_with_hashseed("0", RANDOM_ASSIGNMENT_HASHSEED_SCRIPT)
    assert run_with_hashseed("1", RANDOM_ASSIGNMENT_HASHSEED_SCRIPT) == baseline
    assert run_with_hashseed("2", RANDOM_ASSIGNMENT_HASHSEED_SCRIPT) == baseline


def test_random_assignment_method_receives_original_graph_and_node_labels():
    import networkx as nx

    from gerrychain import Graph, Partition

    nx_graph = nx.path_graph(["node-c", "node-a", "node-b", "node-d"])
    for node in nx_graph:
        nx_graph.nodes[node]["population"] = 1
    graph = Graph.from_networkx(nx_graph)
    received = {}

    def method(*, graph, parts, **kwargs):
        received["graph"] = graph
        received["nodes"] = graph.nodes
        part_labels = list(parts)
        return {node: part_labels[index % 2] for index, node in enumerate(graph.nodes)}

    Partition.from_random_assignment(
        graph,
        n_parts=2,
        epsilon=0,
        pop_col="population",
        method=method,
        rng=2024,
    )

    assert received == {"graph": graph, "nodes": ["node-c", "node-a", "node-b", "node-d"]}


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


def test_ust_recom_is_repeatable_in_process(three_by_three_grid):
    import random

    from gerrychain import Partition, proposals, updaters

    for node in three_by_three_grid:
        three_by_three_grid.node_data(node)["population"] = 1

    def run():
        partition = Partition(
            three_by_three_grid,
            {0: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3},
            {"cut_edges": updaters.cut_edges, "population": updaters.Tally("population")},
        )
        proposal = proposals.ReCom.district_pairs_ust(pop_col="population", pop_target=3, epsilon=0)
        rng = random.Random(2024)
        trajectory = []
        for _ in range(5):
            partition = proposal(partition, rng=rng)
            trajectory.append(sorted(partition.assignment.mapping.items()))
        return trajectory

    assert run() == run()


@pytest.mark.slow
def test_pa_freeze():
    import hashlib

    from gerrychain import (
        GeographicPartition,
        Graph,
        MarkovChain,
        accept,
        constraints,
        updaters,
    )
    from gerrychain.proposals import build_recom_proposal_fn

    graph = Graph.from_json("docs/_static/PA_VTDs.json")

    my_updaters = {"population": updaters.Tally("TOT_POP", alias="population")}
    initial_partition = GeographicPartition(graph, assignment="2011_PLA_1", updaters=my_updaters)

    ideal_population = sum(initial_partition["population"].values()) / len(initial_partition)

    proposal = build_recom_proposal_fn(
        pop_col="TOT_POP",
        pop_target=ideal_population,
        epsilon=0.02,
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
        == "9308a9251f89c58630b68fb4aefadb5923a8c566d129ad4c20af63d53075e8ae"
    )
