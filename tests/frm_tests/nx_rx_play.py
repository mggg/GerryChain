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

# frm TODO: Convert this into a pytest format...

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

import pytest


# Set the random seed so that the results are reproducible!
import random
random.seed(2024)

# Create NX and RX Graph objects with their underlying NX and RX graphs

# Get path to the JSON containing graph data
test_file_path = os.path.abspath(__file__)
cur_directory = os.path.dirname(test_file_path)
path_for_json_file = os.path.join(cur_directory, "gerrymandria.json")
# print("json file is: ", json_file_path)

# Create an NX based Graph object from the JSON
gerrychain_nxgraph = Graph.from_json(path_for_json_file)

# Fetch the NX graph object from inside the Graph object
nxgraph = gerrychain_nxgraph.getNxGraph()

# Create an RX graph object from NX and set node type to be a dictionary to preserve data attributes
rxgraph = rx.networkx_converter(nxgraph, keep_attributes=True)

# Create a Graph object with an RX graph inside
gerrychain_rxgraph = Graph.from_rustworkx(rxgraph)

# frm: ???: TODO:  The set(rxgraph.nodes()) fails because it returns dictionaries which Python does not like...
# nx_set_of_nodes = set(nxgraph.nodes())
# print("len nx_set_of_nodes is: ", len(nx_set_of_nodes))
# rx_set_of_nodes = set(rxgraph.nodes())
# print("len rx_set_of_nodes is: ", len(rx_set_of_nodes))
# print("NX nodes: ", nx_set_of_nodes)
# print("RX nodes: ", rx_set_of_nodes)

print("Testing node data dict")
print("NX data dict for node 1: ", gerrychain_nxgraph.node_data(1))
print("RX data dict for node 1: ", gerrychain_rxgraph.node_data(1))

"""
Stuff to figure out / test:
            * graph data - that is, data on the graph itself.
              * NX
                  graph = nx.Graph(day="Friday")
                  graph['day'] = "Monday"
              * RX
                  graph = rx.PyGraph(attrs=dict(day="Friday"))
                  graph.attrs['day'] = "Monday"
            * graph.nodes
              * NX 
                    This is a NodeView:
                        nodes[x] gives dict for data for the node
              * RX
                    RX does not have this.  Instead it has nodes() which just returns
                    a list/set of the node indices.
                    Actually, a node in RX can be any Python object, but in particular, it
                    can be a dictionary.  In my test case, I think the node in the graph is just
                    an integer, but it should instead be a dict.  Can the value of one node differ
                    from that of another node?  That is, can you have a graph where the nodes are
                    of different types?  This would semantically make no sense, but maybe it is 
                    possible.
                    What is nice about this is that graph[node_id] in RX will be the data for the
                    node - in our case a dictionary.  So the syntax to access a node's data dictionary
                    will be different, but both work:

                      NX:  graph.nodes[node_id]
                      RX:  graph[node_id]

              * Comments:
                    The code had graph.nodes[node_id][value_id] = new_value all over.  I changed
                    the code to instead do graph.node_data(node_id) but I think that 
                    users are used to doing it the old way => need to create a NodeView for RX...
            * graph.edges()
              * NX
              * RX
            * graph.edges[edge]["random_weight"] = weight
              * NX
              * RX
            * graph.node_indices
              * NX
              * RX
            * graph.neighbors(node)
              * NX
              * RX
            * graph.add_edge(node, node)
                => next_node(node) local function needs to return int node ID
              * NX
              * RX
            * graph.degree(node)
              * NX
              * RX
            * iter(graph)
              * NX
              * RX
            * graph._degrees[node]  => what is _degrees?
              * NX
              * RX
            * graph.edges
              * NX
              * RX
"""
