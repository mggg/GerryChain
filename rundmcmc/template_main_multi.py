# Imports for I/O processing

import json
import geopandas as gp
from networkx.readwrite import json_graph
import functools
import os
import datetime

# Imports for RunDMCMC components
# You can look at the list of available functions in each
# corresponding .py file.

from rundmcmc.accept import always_accept

from rundmcmc.chain import MarkovChain

from rundmcmc.make_graph import (add_data_to_graph, construct_graph)

from rundmcmc.partition import Partition

from rundmcmc.proposals import propose_random_flip_no_loops

from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               perimeters, polsby_popper,
                               votes_updaters,
                               interior_boundaries)

from rundmcmc.validity import (L1_reciprocal_polsby_popper,
                               UpperBound,
                               Validator, no_vanishing_districts,
                               refuse_new_splits, single_flip_contiguous,
                               within_percent_of_ideal_population)

from rundmcmc.scores import (efficiency_gap, mean_median,
                             mean_thirdian)

from rundmcmc.run import pipe_to_table

from rundmcmc.output import p_value_report

from vis_output import (hist_of_table_scores, trace_of_table_scores)

# Make a folder for the output
current = datetime.datetime.now()
newdir = "./PAoutputs-" + str(current)[:10] + "-" + str(current)[11:13]\
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
district_col = "rounded11"


# This builds a graph
graph = construct_graph(graph_path)

# Write graph to file
with open(newdir + state_name + 'graph_with_data.json', 'w') as outfile1:
    outfile1.write(json.dumps(json_graph.adjacency_data(graph)))

# Put district on graph
assignment = dict(zip(graph.nodes(), [graph.node[x][district_col] for x in graph.nodes()]))


# Input the shapefile with vote data here
vote_path = "./testData/wes_with_districtings.shp"


# This inputs a shapefile with columns you want to add
df = gp.read_file(vote_path)


# This is the number of elections you want to analyze
num_elections = 2


# Names of shapefile voting data columns go here
election_names = ['2016_Presidential', '2016_Senate']
election_columns = [['T16PRESD', 'T16PRESR'], ['T16SEND', 'T16SENR']]


# This adds the data to the graph
add_data_to_graph(df, graph, [cols for pair in election_columns for cols in pair],
                  id_col=unique_label)


# Desired proposal method
proposal_method = propose_random_flip_no_loops


# Desired acceptance method
acceptance_method = always_accept


# Number of steps to run
steps = 100

print("loaded data")


# Necessary updaters go here
updaters = {
            'population': Tally(pop_col, alias='population'),
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
pop_limit = .01
population_constraint = within_percent_of_ideal_population(initial_partition, pop_limit)

compactness_limit = 1.01 * L1_reciprocal_polsby_popper(initial_partition)
compactness_constraint = UpperBound(L1_reciprocal_polsby_popper, compactness_limit)

validator = Validator([refuse_new_splits, no_vanishing_districts,
                       single_flip_contiguous, population_constraint,
                       compactness_constraint])

# Names of validators for output
# Necessary since bounds don't have __name__'s
list_of_validators = [refuse_new_splits, no_vanishing_districts,
                       single_flip_contiguous, within_percent_of_ideal_population,
                       L1_reciprocal_polsby_popper]


# Add cyclic updaters :(
# updaters['metagraph_degree'] = MetagraphDegree(validator, "metagraph_degree")

# This builds the partition object (again) :(
# initial_partition = Partition(graph, assignment, updaters)

print("setup chain")

# This builds the chain object for us to iterate over
chain = MarkovChain(proposal_method, validator, acceptance_method,
                  initial_partition, total_steps=steps)

print("ran chain")

# Post processing commands go below
# Add Election Scores

scores = {}

scores_for_plots = []

for i in range(num_elections):
    vscores = {
        'Mean-Median' + "\n" +
        election_names[i]: functools.partial(mean_median,
                                             proportion_column_name=election_columns[i][0] + "%"),
        'Mean-Thirdian' + "\n" +
        election_names[i]: functools.partial(mean_thirdian,
                                             proportion_column_name=election_columns[i][0] + "%"),
        'Efficiency Gap' + "\n" +
        election_names[i]: functools.partial(efficiency_gap,
                                             col1=election_columns[i][0],
                                             col2=election_columns[i][1]),
        'L1 Reciprocal Polsby-Popper' + "\n" +
        election_names[i]: L1_reciprocal_polsby_popper}

    scores_for_plots.append(vscores)

    scores = {**scores, **vscores}

# Compute the values of the intial state and the chain
initial_scores = {key: score(initial_partition) for key, score in scores.items()}

table = pipe_to_table(chain, scores, display=True, display_frequency=10,
                      bin_frequency=1)


# P-value reports
pv_dict = {key: p_value_report(key, table[key], initial_scores[key]) for key in scores}
print(pv_dict)
with open(newdir + 'pvals_report_multi.json', 'w') as fp:
    json.dump(pv_dict, fp)

print("computed p-values")


# Write flips to file

allAssignments = {0: chain.state.assignment}

for step in chain:
    allAssignments[chain.counter + 1] = [step.flips]

with open(newdir + "chain_flips_multi.json", "w") as fp:
    json.dump(allAssignments, fp)

print("wrote flips")


# Histogram and trace plotting paths
hist_path = newdir + "chain_histogram_multi_"
trace_path = newdir + "chain_traces_multi_"


# Plots for each election

for i in range(num_elections):

    hist_of_table_scores(table, scores=scores_for_plots[i],
                         outputFile=hist_path + election_names[i] + ".png",
                         num_bins=50, name=state_name + "\n" + election_names[i])

    trace_of_table_scores(table, scores=scores_for_plots[i],
                          outputFile=trace_path + election_names[i] + ".png",
                          name=state_name + "\n" + election_names[i])


print("plotted histograms")
print("plotted traces")


# Record run paramters
with open(newdir + "parameters.txt", "w") as f:
    f.write("Basic Setup Info \n\n")
    f.write("State: " + "\n" + state_name)
    f.write("\n")
    f.write("\n")
    f.write("Initial Plan: " + "\n" + district_col)
    f.write("\n")
    f.write("\n")
    f.write("Elections: ")
    f.write("\n")
    for i in range(num_elections):
        f.write(election_names[i] + "\n")
    f.write("\n")
    f.write("\n")
    f.write("\n")
    f.write("Chain Parameters:")
    f.write("\n")
    f.write("\n")
    f.write("Number of Steps: " + str(steps))
    f.write("\n")
    f.write("\n")
    f.write("Proposal: " + proposal_method.__name__)
    f.write("\n")
    f.write("\n")
    f.write("Acceptance Method: " + acceptance_method.__name__)
    f.write("\n")
    f.write("\n")
    f.write("Validators: ")
    f.write("\n")
    for v in list_of_validators:
        f.write(v.__name__ + "\n")

print("wrote paramters")
