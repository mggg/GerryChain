# Imports for I/O processing
import geopandas as gp
import os
import datetime
import matplotlib.pyplot as plt
import random

# Imports for RunDMCMC components
# You can look at the list of available functions in each
# corresponding .py file.

from rundmcmc.accept import always_accept

from rundmcmc.make_graph import (add_data_to_graph, construct_graph,
                                 get_assignment_dict_from_graph)

from rundmcmc.partition import Partition

from rundmcmc.proposals import propose_random_flip

from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               perimeters, polsby_popper,
                               votes_updaters,
                               interior_boundaries)

from rundmcmc.validity import (L1_reciprocal_polsby_popper,
                               L_minus_1_polsby_popper,
                               UpperBound, LowerBound,
                               Validator, single_flip_contiguous,
                               within_percent_of_ideal_population,
                               SelfConfiguringLowerBound)

from initial_report import write_initial_report

# Set random seed.
random.seed(1769)

for district_col in ["GOV_4_1", "TS_4_1", "2011", "Remedial"]:

    current = datetime.datetime.now()
    newdir = "./Outputs/PA_report-" + str(current)[:10] + "-" + str(current)[11:13]\
             + "-" + str(current)[14:16] + "-" + str(current)[17:19] + "/"

    os.makedirs(os.path.dirname(newdir + "init.txt"), exist_ok=True)
    with open(newdir + "init.txt", "w") as f:
        f.write("Created Folder")

    # Input the path to the graph (either JSON or shapefile) and the label column
    # This file should have at least population, area, and district plan
    state_name = "Pennsylvania"
    graph_path = "./testData/PA_rook.json"
    unique_label = "wes_id"

    # Names of graph columns go here
    pop_col = "population"
    area_col = "area"

    # This builds a graph
    graph = construct_graph(graph_path, data_source_type="json")

    # Write graph to file
    # with open(newdir + state_name + '_graph_with_data.json', 'w') as outfile1:
    #    outfile1.write(json.dumps(json_graph.adjacency_data(graph)))

    # Get assignment dictionary
    assignment = get_assignment_dict_from_graph(graph, district_col)

    # Input the shapefile with vote data here
    vote_path = "./testData/wes_with_districtings.shp"
    # vote_path = "./testData/FinalPA.shp"

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
    # add_data_to_graph(df, graph, ["County"])

    # Geojson for plotting
    df_plot = gp.read_file("./testData/wes_for_plots.geojson")
    df_plot["initial"] = df_plot[unique_label].map(assignment)
    df_plot.plot(column="initial", cmap='tab20')
    plt.axis('off')
    plt.savefig(newdir + "PaExpinitial.png")
    plt.clf()

    # Desired proposal method
    proposal_method = propose_random_flip

    # Desired acceptance method
    acceptance_method = always_accept

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
    # Necessary for computing metagraph degree
    pop_limit = .01
    population_constraint = within_percent_of_ideal_population(initial_partition, pop_limit)

    compactness_limit_L1 = 1.01 * L1_reciprocal_polsby_popper(initial_partition)
    compactness_constraint_L1 = UpperBound(L1_reciprocal_polsby_popper, 1000)

    compactness_limit_Lm1 = .9 * L_minus_1_polsby_popper(initial_partition)
    compactness_constraint_Lm1 = LowerBound(L_minus_1_polsby_popper, compactness_limit_Lm1)

    compactness_PA = SelfConfiguringLowerBound(L_minus_1_polsby_popper, epsilon=.1)

    compactness_PA = SelfConfiguringLowerBound(L_minus_1_polsby_popper, epsilon=0)

    validator = Validator([single_flip_contiguous, population_constraint,
                           compactness_constraint_Lm1])
    print("setup chain")
    outputName = newdir + "Initial_Report.html"

    write_initial_report(newdir=newdir, outputName=outputName, partition=initial_partition,
                         df_to_plot=df_plot,
                         state_name=state_name, district_col=district_col,
                         num_elections=num_elections, election_names=election_names,
                         election_columns=election_columns, df=df,
                         unique_label=unique_label, validator=validator)

    print("Wrote Report")