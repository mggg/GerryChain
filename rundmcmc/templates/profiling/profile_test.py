# This just puts `test_template.py` into a `test_` function for use with
# pytest-profiling.

import logging
import random

import geopandas as gp

from rundmcmc.accept import always_accept
from rundmcmc.chain import MarkovChain
from rundmcmc.make_graph import (add_data_to_graph, construct_graph,
                                 get_assignment_dict_from_graph)
from rundmcmc.partition import Partition
from rundmcmc.proposals import propose_random_flip
from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               interior_boundaries, perimeters, polsby_popper,
                               votes_updaters)
from rundmcmc.validity import (L_minus_1_polsby_popper, LowerBound, Validator,
                               no_vanishing_districts, single_flip_contiguous,
                               within_percent_of_ideal_population)


logging.basicConfig(filename="template.log", format="{name}:{lineno} {msg}",
                    style="{", filemode="w", level=logging.DEBUG)


def test_profile():
    # Set random seed.
    random.seed(1835)

    # Input the path to the graph (either JSON or shapefile) and the label column
    # This file should have at least population, area, and district plan
    graph_path = "../../testData/PA_rook.json"
    unique_label = "wes_id"

    # Names of graph columns go here
    pop_col = "population"
    area_col = "area"
    district_col = "Remedial"

    # This builds a graph
    graph = construct_graph(graph_path, data_source_type="json")

    # Get assignment dictionary
    assignment = get_assignment_dict_from_graph(graph, district_col)

    # Input the shapefile with vote data here
    vote_path = "../../testData/wes_with_districtings.shp"

    # This inputs a shapefile with columns you want to add
    df = gp.read_file(vote_path)
    df = df.set_index(unique_label)

    # This is the number of elections you want to analyze
    num_elections = 2

    # Names of shapefile voting data columns go here
    election_names = ['2016_Presidential', '2016_Senate']
    election_columns = [['T16PRESD', 'T16PRESR'], ['T16SEND', 'T16SENR']]

    # This adds the data to the graph
    add_data_to_graph(df, graph, [cols for pair in election_columns for cols in pair])

    # Desired proposal method
    proposal_method = propose_random_flip

    # Desired acceptance method
    acceptance_method = always_accept

    # Number of steps to run
    steps = 100

    print("loaded data")

    # Necessary updaters go here
    updaters = {'population': Tally(pop_col, alias='population'),
                'perimeters': perimeters,
                'exterior_boundaries': exterior_boundaries,
                'interior_boundaries': interior_boundaries,
                'boundary_nodes': boundary_nodes,
                'cut_edges': cut_edges,
                'areas': Tally(area_col, alias='areas'),
                'polsby_popper': polsby_popper,
                'cut_edges_by_part': cut_edges_by_part}

    # Add the vote updaters for multiple plans

    for i in range(num_elections):
        updaters = {**updaters, **votes_updaters(election_columns[i], election_names[i])}

    # This builds the partition object
    initial_partition = Partition(graph, assignment, updaters)

    # Desired validators go here
    # Can change constants and bounds
    pop_limit = .01
    population_constraint = within_percent_of_ideal_population(initial_partition, pop_limit)

    compactness_limit_Lm1 = .99 * L_minus_1_polsby_popper(initial_partition)
    compactness_constraint_Lm1 = LowerBound(L_minus_1_polsby_popper, compactness_limit_Lm1)

    validator = Validator([no_vanishing_districts,
                        single_flip_contiguous, population_constraint,
                        compactness_constraint_Lm1])

    # Add cyclic updaters :(
    # updaters['metagraph_degree'] = MetagraphDegree(validator, "metagraph_degree")

    # This builds the partition object (again) :(
    # initial_partition = Partition(graph, assignment, updaters)

    print("setup chain")

    # This builds the chain object for us to iterate over
    chain = MarkovChain(proposal_method, validator, acceptance_method,
                        initial_partition, total_steps=steps)

    mod = steps // 10 if steps >= 10 else 1

    for k, step in enumerate(chain):
        if k % mod == 0:
            print("{} / {}".format(k, steps))

    print("ran chain")
