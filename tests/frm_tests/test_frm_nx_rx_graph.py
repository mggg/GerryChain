#######################################################
# frm: Overview of test_frm_nx_rx_graph.py
# 
# This test exists to test how NX and RX differ.
# 
# It will probably evolve into a way to test whether stuff
# works the same in the new Graph object with NX vs. RX
# under the covers...
# 
# 

import matplotlib.pyplot as plt
from gerrychain import (Partition, Graph, MarkovChain,
                        updaters, constraints, accept)
from gerrychain.proposals import recom
from gerrychain.constraints import contiguous
from functools import partial
import pandas

import os
import rustworkx as rx
import networkx as nx


# Set the random seed so that the results are reproducible!
import random
random.seed(2024)


test_file_path = os.path.abspath(__file__)
cur_directory = os.path.dirname(test_file_path)
json_file_path = os.path.join(cur_directory, "gerrymandria.json")
print("json file is: ", json_file_path)

nxgraph = Graph.from_json(json_file_path)
#   frm_graph = FrmGraph.from_json(json_file_path)

print("Created Graph from JSON")

# frm: DEBUGGING:
print("created nxgraph")
print("NX nodes: ", list(nxgraph.nodes))
print("NX edges: ", list(nxgraph.edges))

#   print("created frm_graph")
#   print("FrmGraph nodes: ", list(frm_graph.nodes))
#   print("FrmGraph edges: ", list(frm_graph.edges))


rxgraph = rx.networkx_converter(nxgraph)

print("created rxgraph")
print("RX nodes: ", rxgraph.node_indices())
print("RX edges: ", rxgraph.edge_list())

###    my_updaters = {
###        "population": updaters.Tally("TOTPOP"),
###        "cut_edges": updaters.cut_edges
###    }
###    
###    initial_partition = Partition(
###        nxgraph,
###        assignment="district",
###        updaters=my_updaters
###    )
###    
###    # This should be 8 since each district has 1 person in it.
###    # Note that the key "population" corresponds to the population updater
###    # that we defined above and not with the population column in the json file.
###    ideal_population = sum(initial_partition["population"].values()) / len(initial_partition)
###    
###    proposal = partial(
###        recom,
###        pop_col="TOTPOP",
###        pop_target=ideal_population,
###        epsilon=0.01,
###        node_repeats=2
###    )
###    
###    print("Got proposal")
###    
###    recom_chain = MarkovChain(
###        proposal=proposal,
###        constraints=[contiguous],
###        accept=accept.always_accept,
###        initial_state=initial_partition,
###        total_steps=40
###    )
###    
###    print("Set up Markov Chain")
###    
###    assignment_list = []
###    
###    for i, item in enumerate(recom_chain):
###        print(f"Finished step {i+1}/{len(recom_chain)}")
###        assignment_list.append(item.assignment)
###    
###    print("Enumerated the chain: number of entries in list is: ", len(assignment_list))
###    
###    def test_success():
###        len(assignment_list) == 40
