#
# This tests compatibility between the old/original version of
# the Graph object and the new version that encapsulates the
# graph as a data member - either nx_graph or rx_graph.
#       

import matplotlib.pyplot as plt
from gerrychain import (Partition, Graph, MarkovChain,
                        updaters, constraints, accept)
from gerrychain.graph import OriginalGraph
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

new_graph = Graph.from_json(json_file_path)
old_graph = OriginalGraph.from_json(json_file_path)


print("Created old and new Graph objects from JSON")

# frm: DEBUGGING:
# print("created new_graph")
# print("type of new_graph.nodes is: ", type(new_graph.nodes))
new_graph_nodes = new_graph.nodes
old_graph_nodes = list(old_graph.nodes)
# print("new_graph nodes: ", list(new_graph.nodes))
# print("new_graph edges: ", list(new_graph.edges))
# print("")  # newline
# print("created old_graph")
# print("type of old_graph.nodes is: ", type(old_graph.nodes))
# print("old_graph nodes: ", list(old_graph.nodes))
# print("old_graph edges: ", list(old_graph.edges))

print("testing that graph.nodes have same length")
assert(len(new_graph.nodes) == len(old_graph.nodes)), "lengths disagree"

new_graph_edges = new_graph.edges
old_graph_edges = set(old_graph.edges)
print("testing that graph.edges have same length")
assert(len(new_graph_edges) == len(old_graph_edges)), "lengths disagree"

node_subset = set([1,2,3,4,5])
new_graph_subset = new_graph.subgraph(node_subset)
print("type of new_graph.subset is: ", type(new_graph_subset))
print(new_graph_subset.edges)
old_graph_subset = old_graph.subgraph(node_subset)
print("type of old_graph.subset is: ", type(old_graph_subset))
print(old_graph_subset.edges)

#   print("created frm_graph")
#   print("FrmGraph nodes: ", list(frm_graph.nodes))
#   print("FrmGraph edges: ", list(frm_graph.edges))

print("About to test Graph.predecessors(root)")
pred = new_graph.predecessors(1)
print(list(pred))

# frm: TODO:  Flesh out this test...


#
# The code below is from the regression test - maybe 
# it will be useful in the future, maybe not...
#

###    my_updaters = {
###        "population": updaters.Tally("TOTPOP"),
###        "cut_edges": updaters.cut_edges
###    }
###    
###    initial_partition = Partition(
###        new_graph,
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
