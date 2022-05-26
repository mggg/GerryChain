from dataclasses import dataclass
from typing import Iterable, Tuple
from gerrychain.partition import Partition

# TODO: consider using pydantic
@dataclass
class DiversityStats:
    """
    Stats object that reports the diversity of a given chain.
    """
    unique_plans: int
    unique_districts: int
    steps_taken: int

def collect_diversity_stats(chain: Iterable[Partition]) -> Iterable[Tuple[Partition, DiversityStats]]:
    """
    Determine the diversity of the chain being run. Requires the cut_edges updater.
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
            unique_plans = unique_plans,
            unique_districts = unique_districts,
            steps_taken = steps_taken
        )

        yield partition, stats
