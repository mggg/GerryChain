import networkx

from gerrychain.partition import GeographicPartition, Partition
from gerrychain.proposals import propose_random_flip
from gerrychain.graph import Graph
from gerrychain.updaters import cut_edges
from gerrychain.meta import collect_diversity_stats, DiversityStats


def test_stats_one_step():
    graph = Graph.from_networkx(networkx.complete_graph(3))
    assignment = {0: 1, 1: 1, 2: 2}
    partition = Partition(graph, assignment, {"cut_edges": cut_edges})

    chain = [partition]

    for part, stats in collect_diversity_stats(chain):
        assert isinstance(stats, DiversityStats)
        assert isinstance(part, Partition)

    assert stats.unique_plans == 1
    assert stats.unique_districts == 2
    assert stats.steps_taken == 1


def test_stats_two_steps():
    graph = Graph.from_networkx(networkx.complete_graph(3))

    chain = [
        Partition(graph, {0: 1, 1: 1, 2: 2}, {"cut_edges": cut_edges}),
        Partition(graph, {0: 1, 1: 2, 2: 1}, {"cut_edges": cut_edges}),
    ]

    for part, stats in collect_diversity_stats(chain):
        assert isinstance(stats, DiversityStats)
        assert isinstance(part, Partition)

    assert stats.unique_plans == 2
    assert stats.unique_districts == 4
    assert stats.steps_taken == 2


def test_stats_two_steps_many_duplicate_districts():
    graph = Graph.from_networkx(networkx.complete_graph(3))

    chain = [
        Partition(graph, {0: 1, 1: 2, 2: 3}, {"cut_edges": cut_edges}),
        Partition(graph, {0: 1, 1: 3, 2: 2}, {"cut_edges": cut_edges}),
    ]

    for part, stats in collect_diversity_stats(chain):
        assert isinstance(stats, DiversityStats)
        assert isinstance(part, Partition)

    assert stats.unique_plans == 1
    assert stats.unique_districts == 3
    assert stats.steps_taken == 2


def test_stats_two_steps_duplicate_plans():
    graph = Graph.from_networkx(networkx.complete_graph(3))

    chain = [
        Partition(graph, {0: 1, 1: 2, 2: 3}, {"cut_edges": cut_edges}),
        Partition(graph, {0: 1, 1: 2, 2: 3}, {"cut_edges": cut_edges}),
    ]

    for part, stats in collect_diversity_stats(chain):
        assert isinstance(stats, DiversityStats)
        assert isinstance(part, Partition)

    assert stats.unique_plans == 1
    assert stats.unique_districts == 3
    assert stats.steps_taken == 2
