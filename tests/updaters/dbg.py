import math

import networkx
import pytest

from gerrychain import MarkovChain
from gerrychain.constraints import Validator, no_vanishing_districts
from gerrychain.graph import Graph
from gerrychain.partition import Partition
from gerrychain.proposals import propose_random_flip
import random
from gerrychain.updaters import (Election, Tally, boundary_nodes, cut_edges,
                                 cut_edges_by_part, exterior_boundaries,
                                 exterior_boundaries_as_a_set,
                                 interior_boundaries, perimeter)
from gerrychain.updaters.election import ElectionResults
random.seed(2018)


def create_three_by_three_grid():
    """Returns a graph that looks like this:
    0 1 2
    3 4 5
    6 7 8
    """
    nxgraph = networkx.Graph()
    nxgraph.add_edges_from(
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
    return Graph.from_networkx(nxgraph)





def random_assignment(graph, num_districts):
    assignment = {node: random.choice(range(num_districts)) for node in graph.nodes}
    # Make sure that there are cut edges:
    while len(set(assignment.values())) == 1:
        assignment = {node: random.choice(range(num_districts)) for node in graph.nodes}
    return assignment



def test_vote_proportion_returns_nan_if_total_votes_is_zero(three_by_three_grid):
    election = Election("Mock Election", ["D", "R"], alias="election")
    graph = three_by_three_grid

    for node in graph.nodes:
        for col in election.columns:
            graph.node_data(node)[col] = 0

    updaters = {"election": election}
    assignment = random_assignment(graph, 3)

    partition = Partition(graph, assignment, updaters)

    assert all(
        math.isnan(value)
        for party_percents in partition["election"].percents_for_party.values()
        for value in party_percents.values()
    )


three_by_three_grid =  create_three_by_three_grid()
test_vote_proportion_returns_nan_if_total_votes_is_zero(three_by_three_grid)
