# Import for I/O

import os
import random
import json
import geopandas as gp
from networkx.readwrite import json_graph
import functools
import datetime
import logging
import matplotlib.pyplot as plt

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

from rundmcmc.validity import (L_minus_1_polsby_popper,
                               L1_reciprocal_polsby_popper,
                               Validator, single_flip_contiguous,
                               within_percent_of_ideal_population,
                               SelfConfiguringLowerBound,
                               non_bool_where)

from rundmcmc.scores import (efficiency_gap, mean_median,
                             mean_thirdian, how_many_seats_value,
                             population_range,
                             number_cut_edges, worst_pop,
                             L2_pop_dev,compute_meta_graph_degree,
                             worst_pp, best_pp,
                             node_flipped, flipped_to)

# Set random seed
random.seed(1769)

from rundmcmc.output import p_value_report, hist_of_table_scores, trace_of_table_scores, pipe_to_table


# Here is where you have to input a few things again

# Type the name of your state
state_name = "Arkansas"

# Input the path to the JSON graph and the GEOJSON for plotting
graph_path = "./Data/Arkansas_graph_with_data.json"
plot_path = "./Data/AR_full.geojson"

# Names of graph columns go here
unique_label = "ID"
pop_col = "POP10"
district_col = "CD"
county_col = "ARCOUNTYFP"
area_col = "areas"

# Type the number of elections here
num_elections = 2

# Type the names of the elections here
election_names = ['2016_Senate', '2016_Presedential']

# Type the columns of the corresponding elections here
# ordered like [Republican, Democratic]
election_columns = [['ARV2016S_1', 'ARV2016SEN'], ['ARV2016PRE', 'ARV2016P_1']]

# Choose a proposal from proposals.py
proposal_method = propose_random_flip

# Choose an acceptance method from accept.py
acceptance_method = always_accept

# Choose how many steps to run the chain
steps = 10000

# For outputs type the number of times you would like the values written to the console,
# the frequency to collect stats about the run, and the number of plots to generate
number_to_display = 100
bin_interval = 1
num_plots = 100


# That was (almost) everything!
# The code below constructs and runs the Markov chain
# You may want to adjust the binary constraints -
# they are located below in the section labelled ``Validators''


# Make a folder for the output
current = datetime.datetime.now()
newdir = "./Outputs/" + state_name + "run" + str(current)[:10] + "-" + str(current)[11:13]\
         + "-" + str(current)[14:16] + "-" + str(current)[17:19] + "/"

os.makedirs(os.path.dirname(newdir + "init.txt"), exist_ok=True)
with open(newdir + "init.txt", "w") as f:
    f.write("Created Folder")


# This builds a graph
graph = construct_graph(graph_path, id_col=unique_label, area_col=area_col,
                        pop_col=pop_col, district_col=district_col,
                        data_cols=[county_col]
                        + [cols for pair in election_columns for cols in pair],
                        data_source_type="json")


# Get assignment dictionary
assignment = get_assignment_dict_from_graph(graph, district_col)


# Necessary updaters go here
updaters = {'population': Tally('population'),
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

# Choose which binary constraints to enforce
# Options are in validity.py

pop_limit = .01
population_constraint = within_percent_of_ideal_population(initial_partition, pop_limit)

compactness_constraint_Lm1 = SelfConfiguringLowerBound(L_minus_1_polsby_popper, epsilon=.1)

validator = Validator([single_flip_contiguous, population_constraint, 
                       compactness_constraint_Lm1]) 

# Names of validators for output
# Necessary since bounds don't have __name__'s
list_of_validators = [single_flip_contiguous, within_percent_of_ideal_population,
                      L_minus_1_polsby_popper] 




# Geojson for plotting
df_plot = gp.read_file(plot_path)
df_plot["initial"] = df_plot[unique_label].map(assignment)
df_plot.plot(column="initial", cmap='tab20')
plt.axis('off')
plt.savefig(newdir + district_col + "_initial.png")
plt.close()

print("setup chain")

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

scores3 = {
    "Flipped to:": flipped_to
    }
    
chain_stats = scores.copy()


scores = {**scores, **scores2}
scores = {**scores, **scores3}
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

table = pipe_to_table(chain, scores, display=True, number_to_display=number_to_display,
                      bin_interval=bin_interval)


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
                     num_bins=1000, name=state_name + "\n" + district_col)

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

print("plotting steps")

assignment = get_assignment_dict_from_graph(graph, district_col)

counters = assignment.copy()
plot_assignment = assignment.copy()

for label in list(counters.keys()):
    counters[label]=0

num_steps = 0
plot_interval = steps / num_plots

post_flips = table["Node Flipped:"]
for z in range(steps):
    counters[table[z]["Node Flipped:"]] += 1
    plot_assignment[table[z]["Node Flipped:"]] = table[z]["Flipped to:"]
    
    if num_steps % plot_interval == 0:
        
        print("Drawing step ", num_steps, " Figure")

        df_plot[str(num_steps) + "_steps"] = df_plot[unique_label].map(plot_assignment)

        df_plot.plot(column=str(num_steps) + "_steps", cmap='tab20')

        plt.axis('off')
        plt.savefig(newdir + state_name + "_%04d.png" % num_steps)
        plt.close()
    num_steps += 1


df_plot["num_flips"] = df_plot[unique_label].map(counters)
df_plot.plot(column="num_flips", cmap='tab20')
plt.axis('off')
plt.savefig(newdir + state_name + "_node_flips.png")
plt.close()

plt.hist(df_plot["num_flips"],bins=100)
plt.savefig(newdir + state_name + "_node_flips_hist.png")
plt.close()

# To animate:
# ffmpeg -framerate 5 -i state_name_%04d.png -c:v libx264
# -profile:v high -crf 20 -pix_fmt yuv420p state_name.mp4
