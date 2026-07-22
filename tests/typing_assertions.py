"""Consumer-side assertions for public typing contracts."""

import random
from collections.abc import Hashable, Mapping, Sequence
from typing import Any, assert_type

import networkx
import rustworkx

from gerrychain import Graph, Partition
from gerrychain.accept import AcceptanceFn
from gerrychain.constraints import Bounds, deviation_from_ideal, within_percent_of_ideal_population
from gerrychain.graph import FrozenGraph
from gerrychain.optimization import SingleMetricOptimizer
from gerrychain.optimization.gingleator import GingleScoreFn
from gerrychain.partition.initial_partition_generators import PartitionFn
from gerrychain.proposals import ProposalFn
from gerrychain.tree import BipartitionTreeFn, ReComBipartitionTreeFn, bipartition_tree
from gerrychain.updaters import Tally
from gerrychain.updaters.election import get_percents
from gerrychain.updaters.flows import EdgeFlowUpdateFn


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


def assert_callable_types() -> None:
    """Pin positional and keyword portions of public callable contracts."""

    def consume_contracts(
        proposal_fn: ProposalFn,
        acceptance_fn: AcceptanceFn,
        score_fn: GingleScoreFn,
        edge_flow_fn: EdgeFlowUpdateFn[float],
        bipartition_fn: BipartitionTreeFn,
        recom_bipartition_fn: ReComBipartitionTreeFn,
        partition_fn: PartitionFn,
    ) -> None:
        pass

    def propose(state: Partition, /, *, rng: random.Random) -> Partition:
        return state

    def accept(state: Partition, /, *, rng: random.Random) -> bool:
        return True

    def score(state: Partition, /, *, minority_perc_col: str, threshold: float) -> float:
        return threshold

    def update_edge_flow(
        state: Partition,
        old_value: float,
        /,
        *,
        new_edges: set[tuple[int, int]],
        old_edges: set[tuple[int, int]],
    ) -> float:
        return old_value

    def split_seed_graph(
        source: Graph | FrozenGraph,
        /,
        *,
        pop_col: str,
        pop_target: float,
        epsilon: float,
        node_repeats: int = 0,
        one_sided_cut: bool = False,
        rng: random.Random,
    ) -> frozenset[Hashable]:
        return frozenset()

    def partition_graph(
        *,
        graph: Graph,
        parts: Sequence[Hashable],
        pop_target: float,
        pop_col: str,
        epsilon: float,
        rng: random.Random,
    ) -> dict[Hashable, Hashable]:
        return {}

    consume_contracts(
        propose,
        accept,
        score,
        update_edge_flow,
        split_seed_graph,
        bipartition_tree,
        partition_graph,
    )
