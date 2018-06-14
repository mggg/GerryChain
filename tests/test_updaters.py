import networkx

from rundmcmc.partition import Partition
from rundmcmc.updaters import statistic_factory


def test_Partition_can_update_stats():
    graph = networkx.complete_graph(3)
    assignment = {0: 1, 1: 1, 2: 2}

    graph.nodes[0]['stat'] = 1
    graph.nodes[1]['stat'] = 2
    graph.nodes[2]['stat'] = 3

    updaters = {'total_stat': statistic_factory('stat', alias='total_stat')}

    partition = Partition(graph, assignment, updaters)
    assert partition['total_stat'][2] == 3
    flip = {1: 2}

    new_partition = partition.merge(flip)
    assert new_partition['total_stat'][2] == 5
