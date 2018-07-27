# Imports for I/O processing
import geopandas as gp
import os
import datetime
import matplotlib.pyplot as plt
import random
import pandas as pd

# Imports for RunDMCMC components
# You can look at the list of available functions in each
# corresponding .py file.

from rundmcmc.accept import always_accept

from rundmcmc.chain import MarkovChain

from rundmcmc.make_graph import (add_data_to_graph, construct_graph,
                                 get_assignment_dict_from_graph)

from rundmcmc.partition import Partition

from rundmcmc.proposals import propose_random_flip  #  _no_loops

from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               perimeters, polsby_popper,
                               votes_updaters,
                               interior_boundaries, MetagraphDegree)

from rundmcmc.validity import (L1_reciprocal_polsby_popper,
                               L_minus_1_polsby_popper,
                               UpperBound, LowerBound,
                               Validator, single_flip_contiguous,
                               within_percent_of_ideal_population,
                               SelfConfiguringLowerBound, no_more_disconnected)

from initial_report import write_initial_report

from rundmcmc.entropiesReport import countyEntropyReport, countySplitDistrict


# Set random seed.
random.seed(1769)



# Input the path to the graph (either JSON or shapefile) and the label column
# This file should have at least population, area, and district plan
state_name = "Pennsylvania"
graph_path = "./testData/FinalPA_new.shp"
unique_label = "wes_id"


# Names of graph columns go here
# area_col = "ALAND10"
pop_col = "population"
county_col = "County"


# This builds a graph
graph = construct_graph(graph_path, id_col=unique_label, pop_col=pop_col, data_cols=["GOV", "TS", "2011Plan", "Remedial",
                                   "538dem", "538cpct", "8thgrade", "8thgrade2", "Persily", county_col, 'T16PRESD', 'T16PRESR', 'T16SEND', 'T16SENR'],
                        data_source_type="fiona")


df = gp.read_file(graph_path)

for name in ["GOV", "TS", "2011Plan", "Remedial",
                                   "538dem", "538cpct", "8thgrade", "8thgrade2", "Persily", county_col, 'T16PRESD', 'T16PRESR', 'T16SEND', 'T16SENR']:
    df[name]=pd.to_numeric(df[name], errors='coerce')

# This is the number of elections you want to analyze
num_elections = 2

# Names of shapefile voting data columns go here
election_names = ['2016_Presidential', '2016_Senate']
election_columns = [['T16PRESD', 'T16PRESR'], ['T16SEND', 'T16SENR']]

for district_col in ["GOV", "TS", "2011Plan", "Remedial", "538dem", "538cpt", "8thgrade", "8thgrade2", "Persily"]:
    current = datetime.datetime.now()
    newdir = "./Outputs/PA_report-" + str(current)[:10] + "-" + str(current)[11:13]\
             + "-" + str(current)[14:16] + "-" + str(current)[17:19] + "/"

    os.makedirs(os.path.dirname(newdir + "init.txt"), exist_ok=True)
    with open(newdir + "init.txt", "w") as f:
        f.write("Created Folder")
    # Get assignment dictionary
    assignment = get_assignment_dict_from_graph(graph, district_col)
    for k in assignment.keys():
        assignment[k]=int(assignment[k])

    # Geojson for plotting
    df_plot = gp.read_file("./testData/PA_new.geojson")
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
                'areas': Tally("areas", alias='areas'),
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

    validator = Validator([single_flip_contiguous,population_constraint, 
                           compactness_constraint_Lm1])
    
    print("setup chain")

    outputName = newdir + "Initial_Report.html"
    entropy, county_data = countyEntropyReport(initial_partition,
                                               pop_col=pop_col, county_col=county_col)

    reverse_entropy = countySplitDistrict(initial_partition,
                                          pop_col=pop_col, county_col=county_col)

    write_initial_report(newdir=newdir, outputName=outputName, partition=initial_partition,
                         df_to_plot=df_plot,
                         state_name=state_name, district_col=district_col,
                         num_elections=num_elections, election_names=election_names,
                         election_columns=election_columns, df=df,
                         unique_label=unique_label, validator=validator,
                         county_col=county_col, report_entropy = True, entropy=entropy,
                         county_data=county_data, reverse_entropy=reverse_entropy)


    print("Wrote Report")
