import random

import networkx
import pytest


@pytest.fixture
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
