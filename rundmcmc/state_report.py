# Imports for I/O processing
import geopandas as gp
import os
import datetime
import matplotlib.pyplot as plt
import json
from networkx.readwrite import json_graph

# Imports for RunDMCMC components
# You can look at the list of available functions in each
# corresponding .py file.

from rundmcmc.make_graph import (add_data_to_graph, construct_graph,
                                 get_assignment_dict_from_graph)

from rundmcmc.partition import Partition

from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               perimeters, polsby_popper,
                               votes_updaters,
                               interior_boundaries)

from initial_report import write_initial_report

from entropiesReport import countyEntropyReport, countySplitDistrict


# This is the part you fill out

# Type the ID(s) of your districting plans in this list
# separated by commas if you have more than one

district_cols = ["CD"]

# Type the name of your state here
state_name = "Arkansas"

# Type the paths to your shapefile and geojson
graph_path = "./Data/AR_full.shp"
plot_path = "./Data/AR_full.geojson"

# Type the names of your columns here
unique_label = "ID"
pop_col = "POP10"
county_col = "ARCOUNTYFP"
county_report = True

# Type the number of elections here
num_elections = 2

# Type the names of the elections here
election_names = ['2016_Senate', '2016_Presedential']

# Type the columns of the corresponding elections here
# ordered like [Republican, Democratic]
election_columns = [['ARV2016S_1', 'ARV2016SEN'], ['ARV2016PRE', 'ARV2016P_1']]


# That was it. You don't have to touch anything below!


for district_col in district_cols:

    current = datetime.datetime.now()
    newdir = "./Outputs/" + state_name + "_report-" + str(current)[:10] + "-" + str(current)[11:13]\
             + "-" + str(current)[14:16] + "-" + str(current)[17:19] + "/"

    os.makedirs(os.path.dirname(newdir + "init.txt"), exist_ok=True)
    with open(newdir + "init.txt", "w") as f:
        f.write("Created Folder")

    print("slowly building graph ...")
    # This builds a graph
    graph = construct_graph(graph_path, pop_col=pop_col, id_col=unique_label,
                            district_col=district_col,
                            data_source_type="fiona")

    # Get assignment dictionary
    assignment = get_assignment_dict_from_graph(graph, district_col)

    # This inputs a shapefile with columns you want to add
    df = gp.read_file(graph_path)
    df = df.set_index(unique_label)

    # This adds the data to the graph
    add_data_to_graph(df, graph, [cols for pair in election_columns for cols in pair])
    add_data_to_graph(df, graph, [county_col, pop_col])

    # Write graph to file so it never has to be built again!
    #with open(newdir + state_name + '_graph_with_data.json', 'w') as outfile1:
    #    outfile1.write(json.dumps(json_graph.adjacency_data(graph)))

    # Geojson for plotting
    df_plot = gp.read_file(plot_path)
    df_plot["initial"] = df_plot[unique_label].map(assignment)
    df_plot.plot(column="initial", cmap='tab20')
    plt.axis('off')
    plt.savefig(newdir + district_col + "_initial.png")
    plt.close()

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
    initial_partition = Partition(graph, district_col, updaters)

    print("setup partition")

    outputName = newdir + "Initial_Report.html"
    if county_report is True:

        entropy, county_data = countyEntropyReport(initial_partition,
                                               pop_col=pop_col, county_col=county_col)

        reverse_entropy = countySplitDistrict(initial_partition,
                                          pop_col=pop_col, county_col=county_col)

        write_initial_report(newdir=newdir, outputName=outputName, partition=initial_partition,
                             df_to_plot=df_plot,
                             state_name=state_name, district_col=district_col,
                             num_elections=num_elections, election_names=election_names,
                             election_columns=election_columns, df=df,
                             unique_label=unique_label, validator=None,
                             county_col=county_col, report_entropy=True, entropy=entropy,
                             county_data=county_data, reverse_entropy=reverse_entropy)

    else:
        write_initial_report(newdir=newdir, outputName=outputName, partition=initial_partition,
                         df_to_plot=df_plot,
                         state_name=state_name, district_col=district_col,
                         num_elections=num_elections, election_names=election_names,
                         election_columns=election_columns, df=df,
                         unique_label=unique_label, validator=None)

    print("Wrote Report")
