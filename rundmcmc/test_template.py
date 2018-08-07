# Imports for I/O processing
import os
import json
import geopandas as gp
from networkx.readwrite import json_graph
import functools
import datetime
import matplotlib.pyplot as plt
import random

# Imports for RunDMCMC components
# You can look at the list of available functions in each
# corresponding .py file.

from rundmcmc.accept import always_accept

from rundmcmc.chain import MarkovChain

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
                               Validator, single_flip_contiguous,
                               within_percent_of_ideal_population,
                               SelfConfiguringLowerBound)

from rundmcmc.scores import (efficiency_gap, mean_median,
                             mean_thirdian, how_many_seats_value,
                             number_cut_edges, worst_pop,
                             L2_pop_dev,
                             worst_pp, best_pp,
                             node_flipped)


from rundmcmc.output import (p_value_report, hist_of_table_scores,
                             trace_of_table_scores, pipe_to_table)

from initial_report import write_initial_report

from entropiesReport import countyEntropyReport, countySplitDistrict


# Make a folder for the output
current = datetime.datetime.now()
newdir = "./Outputs/PA_test-" + str(current)[:10] + "-" + str(current)[11:13]\
         + "-" + str(current)[14:16] + "-" + str(current)[17:19] + "/"

os.makedirs(os.path.dirname(newdir + "init.txt"), exist_ok=True)
with open(newdir + "init.txt", "w") as f:
    f.write("Created Folder")


# Input the path to the graph (either JSON or shapefile) and the label column
# This file should have at least population, area, and district plan
print("loading data")
state_name = "Pennsylvania"
graph_path = "./Data/final_PA_vtds.shp"
unique_label = "ID"


# Names of graph columns go here
pop_col = "P0050001"
district_col = "Remedial"


# This builds a graph
print("building graph ... slowly")
graph = construct_graph(graph_path, id_col=unique_label,
                        pop_col=pop_col, district_col=district_col,
                        data_source_type="fiona")


# Get assignment dictionary
assignment = get_assignment_dict_from_graph(graph, district_col)


# Input the shapefile with vote data here
vote_path = "./Data/final_PA_vtds.shp"

# This inputs a shapefile with columns you want to add
print("adding elections")
df = gp.read_file(vote_path)
df = df.set_index(unique_label)
county_col = "COUNTY"

# This is the number of elections you want to analyze
num_elections = 9


# Names of shapefile voting data columns go here
election_names = ["Governor_2010", "Senate_2010", "AttorneyGeneral_2012", "President_2012",
                  "Senate_2012", "Governor_2014", "AttorneyGeneral_2016",
                  "Presdent_2016", "Senate_2016"]
election_columns = [["GOV10R", "GOV10D"], ["SEN10R", "SEN10D"], ["ATG12R", "ATG12D"],
    ["PRES12R", "PRES12D"], ["USS12R", "USS12D"], ["F2014GovR", "F2014GovD"],
    ["T16ATGR", "T16ATGD"], ["T16PRESR", "T16PRESD"], ["T16SENR", "T16SEND"]]


# This adds the data to the graph
add_data_to_graph(df, graph, [cols for pair in election_columns for cols in pair])
add_data_to_graph(df, graph, [county_col])


# Write graph to file
with open(newdir + state_name + '_graph_with_data.json', 'w') as outfile1:
    outfile1.write(json.dumps(json_graph.adjacency_data(graph)))

# Geojson for plotting
df_plot = gp.read_file("./Data/final_PA_vtds.geojson" )
df_plot["initial"] = df_plot[unique_label].map(assignment)

df_plot.plot(column="initial", cmap='tab20')

plt.axis('off')
plt.savefig(newdir + "PaExpinitial.png")
plt.clf()



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
            'areas': Tally('areas'),
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

compactness_PA = SelfConfiguringLowerBound(L_minus_1_polsby_popper, epsilon=.1)

validator = Validator([single_flip_contiguous, population_constraint,
                       compactness_PA])

# Names of validators for output
# Necessary since bounds don't have __name__'s
list_of_validators = [single_flip_contiguous, within_percent_of_ideal_population,
                      L_minus_1_polsby_popper] 


print("setup chain")

outputName = newdir + "Initial_Report.html"

entropy, county_data = countyEntropyReport(initial_partition,
                                           pop_col=pop_col, county_col=county_col)

reverse_entropy = countySplitDistrict(initial_partition,
                                      pop_col=pop_col, county_col=county_col)
print("writing report")
write_initial_report(newdir=newdir, outputName=outputName, partition=initial_partition,
                     df_to_plot=df_plot,
                     state_name=state_name, district_col=district_col,
                     num_elections=num_elections, election_names=election_names,
                     election_columns=election_columns, df=df,
                     unique_label=unique_label, validator=validator,
                     county_col=county_col, report_entropy=True, entropy=entropy,
                     county_data=county_data, reverse_entropy=reverse_entropy)

print("wrote report")


# This builds the chain object for us to iterate over
chain = MarkovChain(proposal_method, validator, acceptance_method,
                    initial_partition, total_steps=steps)

print("built chain")

# Post processing commands go below
# Adds election Scores

scores = {
    'L1 Reciprocal Polsby-Popper': L1_reciprocal_polsby_popper,
    'L -1 Polsby-Popper': L_minus_1_polsby_popper,
    'Worst Population': worst_pop,
    'Conflicted Edges': number_cut_edges,
    }

scores2 = {
    "L2 population deviation": L2_pop_dev,
    "Worst PP score:": worst_pp,
    "Best PP score:": best_pp,
    "Node Flipped": node_flipped
    }
    
chain_stats = scores.copy()


scores = {**scores, **scores2}
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
        'Number of Democratic Seats' + "\n" +
        election_names[i]: functools.partial(how_many_seats_value,
                                             col1=election_columns[i][0],
                                             col2=election_columns[i][1])
        }

    scores_for_plots.append(vscores)

    scores = {**scores, **vscores}

# Compute the values of the intial state and the chain
initial_scores = {key: score(initial_partition) for key, score in scores.items()}

table = pipe_to_table(chain, scores, display=True, number_to_display=100,
                      bin_interval=1)


# P-value reports
pv_dict = {key: p_value_report(key, table[key], initial_scores[key]) for key in scores}
# print(pv_dict)
with open(newdir + 'pvals_report_multi.json', 'w') as fp:
    json.dump(pv_dict, fp)

print("computed p-values")

# Histogram and trace plotting paths
hist_path = newdir + "chain_histogram_multi_"
trace_path = newdir + "chain_traces_multi_"


# Plots for each election

for i in range(num_elections):

    hist_of_table_scores(table, scores=scores_for_plots[i],
                         outputFile=hist_path + election_names[i] + ".png",
                         num_bins=100, name=state_name + "\n" + election_names[i])

    trace_of_table_scores(table, scores=scores_for_plots[i],
                          outputFile=trace_path + election_names[i] + ".png",
                          name=state_name + "\n" + election_names[i])


# Plot for chain stats

hist_of_table_scores(table, scores=chain_stats,
                     outputFile=hist_path + "stats.png",
                     num_bins=100, name=state_name + "\n" + district_col)

trace_of_table_scores(table, scores=chain_stats,
                      outputFile=trace_path + "stats.png",
                      name=state_name + "\n" + district_col)

hist_of_table_scores(table, scores=scores2,
                     outputFile=hist_path + "stats2.png",
                     num_bins=1000, name=state_name + "\n" + district_col)

trace_of_table_scores(table, scores=scores2,
                      outputFile=trace_path + "stats2.png",
                      name=state_name + "\n" + district_col)


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
    f.write("Binary Constraints: ")
    f.write("\n")
    for v in list_of_validators:
        f.write(v.__name__ + "\n")

print("wrote paramters")

for part in chain:

    Last_assn = part.assignment
    df_plot["final"] = df_plot[unique_label].map(Last_assn)
    df_plot.plot(column="final", cmap='tab20')
    plt.axis('off')
    plt.savefig(newdir + "PaExpfinal.png")
    plt.close()
    break

print("all done :)")
