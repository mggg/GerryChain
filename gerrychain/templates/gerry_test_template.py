# Import for I/O

import os
import random
import json
import geopandas as gpd
import functools
import datetime
import matplotlib.pyplot as plt
import time
from functools import partial


# Imports for gerryChain components
# You can look at the list of available functions in each
# corresponding .py file or the github docs. 

import gerrychain as gc
from gerrychain import Graph
import matplotlib.pyplot as plt
from gerrychain import MarkovChain
from gerrychain.constraints import Validator, single_flip_contiguous
from gerrychain.proposals import propose_random_flip
from gerrychain.accept import always_accept
from gerrychain.updaters import Election
from gerrychain import GeographicPartition
from tree_proposals import *
from tree_methods import *

# Here is where you have to input a few things again

# Set a random seed for reproducibility
random.seed(1769)

# Type the name of your state
state_name = "MA"

# Input the path to the JSON graph and the shapefile for plotting
graph_path = "./Data/MA_graph.json"
plot_path = "./Data/MA_Precincts_12_16.shp"



#Next we need to collect some information about the data columns on the graph
unique_label = "GEOID"
pop_col = "POP10"
district_col = "CD"
county_col = "City/Town"

# Type the number of elections here
num_elections = 5

# Type the names of the elections here
election_names  = ["SEN12","PRES12","SEN13","SEN14","PRES16"]

# Type the names of the corresponding election columns here (Democratic party first)

election_columns = [["SEN12D","SEN12R"],["PRES12D","PRES12R"],["SEN13D","SEN13R"],
["SEN14D","SEN14R"],["PRES16D","PRES16R"]]


election_updatesr=dict()
for i in range(num_elections):
    election_updaters[election_names[i]]=Election(election_names[i],
	{"DEM":election_columns[i][0],"GOP":election_columns[i][1]},alias=election_names[i])
	
	



pop_updater = {"population":Tally(pop_col,alias="population")}







df = gpd.read_file("./AR_Full/AR_Full.shp")
ar1=Graph.from_file("./AR_Full/AR_Full.shp")



#arelect = Election ("Senate 2016", {"Dem":"ARV2016SEN","Rep":"ARV2016S_1"},alias="SEN16")
arinit= GeographicPartition(ar1,assignment="CD",updaters={**electionupdaters,**pop_updater)
merge_prop =partial(propose_merge2_tree_partial,pop_col="POP10",epsilon=.05,node_repeats=1)
archain = MarkovChain(proposal = merge_prop, is_valid=Validator([]),accept=always_accept,initial_state=arinit, total_steps=10)
t=0
for part in archain:
    df["plot"+str(t)]=df["LG"].map(part.assignment)
    df.plot(column="plot"+str(t),cmap="tab20")
    plt.show()
    t=t+1





#    print(len(part["cut_edges"]))
	
	
#	single_flip_contiguous