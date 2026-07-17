import math
import random
from typing import cast

import networkx

from gerrychain.graph import Graph
from gerrychain.partition import Partition
from gerrychain.updaters import Election

random.seed(2018)


def create_three_by_three_grid():
    """Returns a graph that looks like this:
    0 1 2
    3 4 5
    6 7 8
    """
    nx_graph = networkx.Graph()
    nx_graph.add_edges_from(
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
    return Graph.from_networkx(nx_graph)


def random_assignment(graph: Graph, num_districts: int):
    assignment = {node: random.choice(range(num_districts)) for node in graph.nodes}
    # Make sure that there are cut edges:
    while len(set(assignment.values())) == 1:
        assignment = {node: random.choice(range(num_districts)) for node in graph.nodes}
    return assignment


def test_vote_proportion_returns_nan_if_total_votes_is_zero(three_by_three_grid: Graph):
    election = Election("Mock Election", ["D", "R"], alias="election")
    graph = three_by_three_grid

    for node in graph.nodes:
        for col in cast("list[str]", election.node_attribute_names):
            graph.node_data(node)[col] = 0

    updaters = {"election": election}
    assignment = random_assignment(graph, 3)

    partition = Partition(graph, assignment, updaters)

    assert all(
        math.isnan(value)
        for party_percents in partition["election"].percents_for_party.values()
        for value in party_percents.values()
    )


three_by_three_grid = create_three_by_three_grid()
test_vote_proportion_returns_nan_if_total_votes_is_zero(three_by_three_grid)
