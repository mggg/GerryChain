"""
Simple tooling to collect diversity stats on chain runs
"""

from dataclasses import dataclass
from typing import Iterable, Tuple
from gerrychain.partition import Partition


@dataclass
class DiversityStats:
    """
    Lightweight stats object that reports the diversity of a given chain.

    :ivar unique_plans: The number of unique plans seen so far.
    :type unique_plans: int
    :ivar unique_districts: The number of unique districts seen so far.
    :type unique_districts: int
    :ivar steps_taken: The number of steps taken so far.
    :type steps_taken: int

    Example usage::

        DiversityStats(unique_plans=44162, unique_districts=82992, steps_taken=100000)
    """

    unique_plans: int
    unique_districts: int
    steps_taken: int


def collect_diversity_stats(
    chain: Iterable[Partition],
) -> Iterable[Tuple[Partition, DiversityStats]]:
    """
    Report the diversity of the chain being run, live, as a drop-in wrapper.
    Requires the cut_edges updater on each `Partition` object. Plans/districts
    are considered distinct if they are not isomorphic. That is, relabled plans
    and districts are considered non-unique and counted as duplicate.

    Example usage::

        for partition, stats in collect_diversity_stats(
            Replay(
                graph,
                "sample-run.chain"
                )
        ):
            print(stats)
            # normal chain stuff here

    :param chain: A chain object to collect stats on.
    :type chain: Iterable[Partition]

    :returns: An iterable of `(partition, DiversityStat)`.
    :rtype: Iterable[Tuple[Partition, DiversityStats]]
    """
    seen_plans = {}
    seen_districts = {}

    unique_plans = 0
    unique_districts = 0
    steps_taken = 0

    for partition in chain:
        steps_taken += 1

        for district, nodes in partition.assignment.parts.items():
            hashable_nodes = tuple(sorted(list(nodes)))
            if hashable_nodes not in seen_districts:
                unique_districts += 1
                seen_districts[hashable_nodes] = 1

        cut_edges = partition["cut_edges"]
        hashable_cut_edges = tuple(sorted(list(cut_edges)))
        if hashable_cut_edges not in seen_plans:
            unique_plans += 1
            seen_plans[hashable_cut_edges] = 1

        stats = DiversityStats(
            unique_plans=unique_plans,
            unique_districts=unique_districts,
            steps_taken=steps_taken,
        )

        yield partition, stats
