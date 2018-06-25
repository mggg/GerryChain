import json

import geopandas as gp
import networkx.readwrite

from rundmcmc.accept import always_accept
from rundmcmc.chain import MarkovChain
from rundmcmc.make_graph import add_data_to_graph, get_assignment_dict
from rundmcmc.partition import Partition
from rundmcmc.proposals import propose_random_flip
from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               perimeters)
from rundmcmc.updaters import polsby_popper_updater as polsby_popper
from rundmcmc.updaters import votes_updaters
from rundmcmc.validity import (Validator, districts_within_tolerance,
                               no_vanishing_districts, single_flip_contiguous)

default_validator = Validator(
    [single_flip_contiguous, no_vanishing_districts, districts_within_tolerance])


def example_partition():
    df = gp.read_file("./testData/mo_cleaned_vtds.shp")

    with open("./testData/MO_graph.json") as f:
        graph_json = json.load(f)

    graph = networkx.readwrite.json_graph.adjacency_graph(graph_json)

    assignment = get_assignment_dict(df, "GEOID10", "CD")

    add_data_to_graph(df, graph, ['PR_DV08', 'PR_RV08', 'POP100', 'ALAND10', 'AWATER10'],
                      id_col='GEOID10')

    updaters = {
        **votes_updaters(['PR_DV08', 'PR_RV08'], election_name='08'),
        'population': Tally('POP100', alias='population'),
        'areas': Tally('ALAND10', alias='areas'),
        'perimeters': perimeters,
        'exterior_boundaries': exterior_boundaries,
        'boundary_nodes': boundary_nodes,
        'polsby_popper': polsby_popper,
        'cut_edges': cut_edges,
        'cut_edges_by_part': cut_edges_by_part
    }
    return Partition(graph, assignment, updaters)


class BasicChain(MarkovChain):
    """
    A basic MarkovChain. The proposal is a single random flip at the boundary of a district.
    A step is valid if the districts are connected, no districts disappear, and the
    populations of the districts are all within 1% of one another.
    Accepts every valid proposal.

    Requires 'cut_edges' and 'population' updaters.
    """

    def __init__(self, initial_state, total_steps=1000):
        """
        :initial_state: the initial graph partition. Must have a cut_edges updater
        :total_steps: (defaults to 1000) the total number of steps that the random walk
        should perform.
        """
        if not initial_state['cut_edges']:
            raise ValueError('BasicChain needs the Partition to have a cut_edges updater.')

        if not initial_state['population']:
            raise ValueError('BasicChain needs the Partition to have a population updater.')

        super().__init__(propose_random_flip, default_validator,
                         always_accept, initial_state, total_steps=total_steps)
