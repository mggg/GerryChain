import networkx

from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.updaters import statistic_factory, cut_edges, crosses_parts
from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph, pull_districts, get_list_of_data, add_data_to_graph
from rundmcmc.validity import Validator, contiguous, single_flip_contiguous
from rundmcmc.chain import MarkovChain


def three_by_three_grid():
    """Returns a graph that looks like this:
    0 1 2
    3 4 5
    6 7 8
    """
    graph = networkx.Graph()
    graph.add_edges_from([(0, 1), (0, 3), (1, 2), (1, 4), (2, 5), (3, 4),
                         (3, 6), (4, 5), (4, 7), (5, 8), (6, 7), (7, 8)])
    return graph


def edge_set_equal(set1, set2):
    return {(y, x) for x, y in set1} | set1 == {(y, x) for x, y in set2} | set2


def test_implementation_of_cut_edges_matches_naive_method():
    graph = three_by_three_grid()
    assignment = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2}
    updaters = {'cut_edges': cut_edges}
    partition = Partition(graph, assignment, updaters)

    flip = {4: 2}
    new_assignment = {**assignment, **flip}
    result = cut_edges(partition, new_assignment, flip)

    naive_cut_edges = {edge for edge in graph.edges if crosses_parts(
        new_assignment, edge)}

    print(result)
    print(naive_cut_edges)

    assert edge_set_equal(result, naive_cut_edges)


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


# TODO: Make a smaller, easier to check test.
def test_single_flip_contiguity_equals_contiguity():
    import random
    random.seed(1887)

    def equality_validator(partition):
        val = partition["contiguous"] == partition["flip_check"]
        assert val
        return partition["contiguous"]

    graph = construct_graph(*ingest("rundmcmc/testData/wyoming_test.shp", "GEOID"))

    cd_data = get_list_of_data("rundmcmc/testData/wyoming_test.shp", ["CD"])
    add_data_to_graph(cd_data, graph, ["CD"])

    assignment = pull_districts(graph, "CD")

    validator = Validator([equality_validator])
    updaters = {"contiguous": contiguous, "cut_edges": cut_edges,
        "flip_check": single_flip_contiguous}

    initial_partition = Partition(graph, assignment, updaters)
    accept = lambda x: True

    chain = MarkovChain(propose_random_flip, validator, accept, initial_partition, total_steps=1000)
    list(chain)
