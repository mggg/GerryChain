"""Consumer-side assertions for public typing contracts."""

from collections.abc import Hashable, Mapping
from typing import Any, assert_type

import networkx
import rustworkx

from gerrychain import Graph, Partition
from gerrychain.constraints import Bounds, deviation_from_ideal, within_percent_of_ideal_population
from gerrychain.optimization import SingleMetricOptimizer
from gerrychain.updaters import Tally
from gerrychain.updaters.election import get_percents


def assert_public_types(
    graph: Graph,
    partition: Partition,
    optimizer: SingleMetricOptimizer,
    counts: Mapping[Hashable, float],
    nx_graph: networkx.Graph[str, dict[str, int], dict[str, float]],
    rx_graph: rustworkx.PyGraph[dict[str, int], dict[str, float]],
) -> None:
    """Pin public types from a package consumer's perspective."""
    assert_type(graph.node_data(0), dict[str, Any])
    assert_type(Graph.from_networkx(nx_graph), Graph)
    assert_type(Graph.from_rustworkx(rx_graph), Graph)
    assert_type(Partition(nx_graph, {"node": "district"}), Partition)

    assert_type(partition.parts, dict[Hashable, frozenset[Hashable]])
    assert_type(partition.flip({0: "district"}), Partition)

    assert_type(optimizer.best_part, Partition | None)
    assert_type(optimizer.best_score, float | None)

    population_bound = within_percent_of_ideal_population(partition)
    assert_type(population_bound, Bounds[[Partition]])
    assert_type(deviation_from_ideal(partition), dict[Hashable, float])

    assert_type(Tally("population")(partition), dict[Hashable, float])
    assert_type(get_percents(counts, counts), dict[Hashable, float])
