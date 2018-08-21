import random

from rundmcmc.updaters.tally import DataTally
from rundmcmc.partition import Partition


def random_assignment(graph, num_districts):
    return {node: random.choice(range(num_districts)) for node in graph.nodes}


def test_data_tally_works_as_an_updater(three_by_three_grid):
    assignment = random_assignment(three_by_three_grid, 4)
    data = {node: random.randint(1, 100) for node in three_by_three_grid.nodes}
    updaters = {'tally': DataTally(data, alias='tally')}
    partition = Partition(three_by_three_grid, assignment, updaters)

    flip = {random.choice(list(partition.graph.nodes)): random.choice(range(4))}
    new_partition = partition.merge(flip)

    assert new_partition['tally']


def test_data_tally_gives_expected_value(three_by_three_grid):
    assignment = {node: 1 for node in three_by_three_grid.nodes}
    data = {node: 1 for node in three_by_three_grid}
    updaters = {'tally': DataTally(data, alias='tally')}
    partition = Partition(three_by_three_grid, assignment, updaters)

    flip = {list(three_by_three_grid.nodes)[0]: 0}
    new_partition = partition.merge(flip)

    assert new_partition['tally'][1] == partition['tally'][1] - 1


def test_from_node_attribute_method_mimics_old_tally(graph_with_random_data_factory):
    graph = graph_with_random_data_factory(['total'])

    updaters = {'total': DataTally.from_node_attribute(graph, 'total', alias='total')}
    assignment = {i: 1 if i in range(4) else 2 for i in range(9)}

    partition = Partition(graph, assignment, updaters)
    expected_total_in_district_one = sum(
        graph.nodes[i]['total'] for i in range(4))
    assert partition['total'][1] == expected_total_in_district_one
