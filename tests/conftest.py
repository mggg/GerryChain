import pytest

from gerrychain import Graph, Partition
import random
from gerrychain.updaters import cut_edges
import networkx as nx

random.seed(2018)


@pytest.fixture
def three_by_three_grid():
    """Returns a graph that looks like this:
    0 1 2
    3 4 5
    6 7 8
    """
    graph = Graph()
    graph.add_edges_from(
        [
            (0, 1),
            (0, 3),
            (1, 2),
            (1, 4),
            (2, 5),
            (3, 4),
            (3, 6),
            (4, 5),
            (4, 7),
            (5, 8),
            (6, 7),
            (7, 8),
        ]
    )
    return graph


@pytest.fixture
def four_by_five_grid_for_opt():
    #  1  2  2  2  2
    #  1  2  1  1  2
    #  1  2  2  1  2
    #  1  1  1  1  2

    # 15 16 17 18 19
    # 10 11 12 13 14
    #  5  6  7  8  9
    #  0  1  2  3  4

    graph = Graph()
    graph.add_nodes_from(
        [
            (0, {"population": 10, "opt_value": 1, "MVAP": 2}),
            (1, {"population": 10, "opt_value": 1, "MVAP": 2}),
            (2, {"population": 10, "opt_value": 1, "MVAP": 2}),
            (3, {"population": 10, "opt_value": 1, "MVAP": 2}),
            (4, {"population": 10, "opt_value": 2, "MVAP": 2}),
            (5, {"population": 10, "opt_value": 1, "MVAP": 2}),
            (6, {"population": 10, "opt_value": 2, "MVAP": 2}),
            (7, {"population": 10, "opt_value": 2, "MVAP": 2}),
            (8, {"population": 10, "opt_value": 1, "MVAP": 2}),
            (9, {"population": 10, "opt_value": 2, "MVAP": 2}),
            (10, {"population": 10, "opt_value": 1, "MVAP": 6}),
            (11, {"population": 10, "opt_value": 2, "MVAP": 6}),
            (12, {"population": 10, "opt_value": 1, "MVAP": 6}),
            (13, {"population": 10, "opt_value": 1, "MVAP": 4}),
            (14, {"population": 10, "opt_value": 2, "MVAP": 4}),
            (15, {"population": 10, "opt_value": 1, "MVAP": 6}),
            (16, {"population": 10, "opt_value": 2, "MVAP": 6}),
            (17, {"population": 10, "opt_value": 2, "MVAP": 6}),
            (18, {"population": 10, "opt_value": 2, "MVAP": 4}),
            (19, {"population": 10, "opt_value": 2, "MVAP": 4}),
        ]
    )

    graph.add_edges_from(
        [
            (0, 1),
            (0, 5),
            (1, 2),
            (1, 6),
            (2, 3),
            (2, 7),
            (3, 4),
            (3, 8),
            (4, 9),
            (5, 6),
            (5, 10),
            (6, 7),
            (6, 11),
            (7, 8),
            (7, 12),
            (8, 9),
            (8, 13),
            (9, 14),
            (10, 11),
            (10, 15),
            (11, 12),
            (11, 16),
            (12, 13),
            (12, 17),
            (13, 14),
            (13, 18),
            (14, 19),
            (15, 16),
            (16, 17),
            (17, 18),
            (18, 19),
        ]
    )

    return graph


@pytest.fixture
def graph_with_random_data_factory(three_by_three_grid):
    def factory(columns):
        graph = three_by_three_grid
        attach_random_data(graph, columns)
        return graph

    return factory


def attach_random_data(graph, columns):
    for node in graph.nodes:
        for col in columns:
            graph.nodes[node][col] = random.randint(1, 1000)


@pytest.fixture
def graph(three_by_three_grid):
    return three_by_three_grid


@pytest.fixture
def example_partition():
    graph = Graph.from_networkx(nx.complete_graph(3))
    assignment = {0: 1, 1: 1, 2: 2}
    partition = Partition(graph, assignment, {"cut_edges": cut_edges})
    return partition


# From the docs: https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
