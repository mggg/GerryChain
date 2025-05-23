#######################################################
# Overview of test_frm_nx_rx_graph.py
#######################################################
"""
 
A collection of tests to verify that the new GerryChain 
Graph object works the same with NetworkX and RustworkX.


"""

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

############################################################
# Create Graph Objects - both direct NX.Graph and RX.PyGraph
# objects and two GerryChain Graph objects that embed the 
# NX and RX graphs.
############################################################

@pytest.fixture(scope="module")
def json_file_path():
    # Get path to the JSON containing graph data
    test_file_path = os.path.abspath(__file__)
    cur_directory = os.path.dirname(test_file_path)
    path_for_json_file = os.path.join(cur_directory, "gerrymandria.json")
    # print("json file is: ", json_file_path)
    return path_for_json_file

@pytest.fixture(scope="module")
def gerrychain_nxgraph(json_file_path):
    # Create an NX based Graph object from the JSON
    graph = Graph.from_json(json_file_path)
    print("gerrychain_nxgraph: len(graph): ", len(graph))
    return(graph)

@pytest.fixture(scope="module")
def nxgraph(gerrychain_nxgraph):
    # Fetch the NX graph object from inside the Graph object
    return gerrychain_nxgraph.getNxGraph()

@pytest.fixture(scope="module")
def rxgraph(nxgraph):
    # Create an RX graph object from NX, preserving node data
    return rx.networkx_converter(nxgraph, keep_attributes=True)

@pytest.fixture(scope="module")
def gerrychain_rxgraph(rxgraph):
    # Create a Graph object with an RX graph inside
    return Graph.from_rustworkx(rxgraph)

##################
# Start of Tests
##################

def test_sanity():
    # frm: if you call pytest with -rP, then it will show stdout for tests
    print("test_sanity(): called")
    assert True

def test_nx_rx_sets_of_nodes_agree(nxgraph, rxgraph):
    nx_set_of_nodes = set(nxgraph.nodes())
    rx_set_of_nodes = set(rxgraph.node_indices())
    assert nx_set_of_nodes == rx_set_of_nodes

def test_nx_rx_node_data_agree(gerrychain_nxgraph, gerrychain_rxgraph):
    nx_data_dict = gerrychain_nxgraph.get_node_data_dict(1)
    rx_data_dict = gerrychain_rxgraph.get_node_data_dict(1)
    assert nx_data_dict == rx_data_dict

def test_nx_rx_node_indices_agree(gerrychain_nxgraph, gerrychain_rxgraph):
    nx_node_indices = gerrychain_nxgraph.node_indices
    rx_node_indices = gerrychain_rxgraph.node_indices
    assert nx_node_indices == rx_node_indices

def test_nx_rx_edges_agree(gerrychain_nxgraph, gerrychain_rxgraph):
    # TODO:  Rethink this test.  At the moment it relies on the edge_list()
    #           call which does not exist on a GerryChain Graph object
    #           being handled by RX through clever __getattr__ stuff.
    #           I think we should add an edge_list() method to GerryChain Graph
    nx_edges = set(gerrychain_nxgraph.edges)
    rx_edges = set(gerrychain_rxgraph.edge_list())
    assert nx_edges == rx_edges

def test_nx_rx_node_neighbors_agree(gerrychain_nxgraph, gerrychain_rxgraph):
    for i in gerrychain_nxgraph:
        # Need to convert to set, because ordering of neighbor nodes differs in the lists
        nx_neighbors = set(gerrychain_nxgraph.neighbors(i))
        rx_neighbors = set(gerrychain_rxgraph.neighbors(i))
        assert nx_neighbors == rx_neighbors

def test_nx_rx_subgraphs_agree(gerrychain_nxgraph, gerrychain_rxgraph):
    subgraph_nodes = [0,1,2,3,4,5]      # TODO: make this a fixture dependent on JSON graph
    nx_subgraph = gerrychain_nxgraph.subgraph(subgraph_nodes)
    rx_subgraph = gerrychain_rxgraph.subgraph(subgraph_nodes)
    for node_id in nx_subgraph:
        nx_node_data = nx_subgraph.get_node_data_dict(node_id)
        rx_node_data = rx_subgraph.get_node_data_dict(node_id)
        assert nx_node_data == rx_node_data
    # frm: TODO:  This does not test that the rx_subgraph has the exact same number of
    #                   nodes as the nx_subgraph, and it does not test edge data...

def test_nx_rx_degrees_agree(gerrychain_nxgraph, gerrychain_rxgraph):
    # Verify that the degree of each node agrees between NX and RX versions
    nx_degrees = {
      node_id: gerrychain_nxgraph.degree(node_id) for node_id in gerrychain_nxgraph.node_indices
    }
    rx_degrees = {
      node_id: gerrychain_rxgraph.degree(node_id) for node_id in gerrychain_rxgraph.node_indices
    }
    for node_id in gerrychain_nxgraph.node_indices:
        assert nx_degrees[node_id] == rx_degrees[node_id]


"""
frm: TODO:

    * Functions:
        * predecessors()
        * successors()
        * is_connected()
        * laplacian_matrix()
        * normalized_laplacian_matrix()
        * neighbors()
            I think this has been done for both NX and RX
        * networkx.generators.lattice.grid_2d_graph()
        * nx.to_dict_of_lists()
        * nx.tree.minimum_spanning_tree()
        * nx.number_connected_components()
        * nx.set_edge_attributes()
        * nx.set_node_attributes()

    * Syntax:
        * graph.edges
            NX - note that edges and edges() do exactly the same thing.  They return
                 an EdgeView of a list of edges with edge_id being a tuple indicating
                 the start and end node_ids for the edge.
                 Need to find out how edges and edges() is used in the code to know
                 what the right thing to do is for RX - that is, what aspect of an
                 EdgeView is used in the code?  Is a set of tuples OK?
        * graph.nodes
            NX returns a NodeView with the node_ids for the nodes
            RX does not have a "nodes" attribute, but it does have a nodes()
            method which does something different.  It returns a list (indexed
            by node_id) of the data associated with nodes.
            So, I need to see how Graph.nodes is used in the code to see what the
            right way is to support it in RX.
        * graph.nodes[node_id]
            returns data dictionary for the node
        * graph.nodes[node_id][attr_id]
            returns the value for the given attribute for that node's data
        * graph.add_edge()
            Done differently in NX and RX
        * graph.degree
        * graph.subgraph
        * for edge in graph.edge_indices:
           graph.edges[edge]["weight"] = random.random()
             In RX, assigning the weight to an edge is done differently...
             Note that edge_indices currently works exactly the same for both
             NX and RX - returning a set of tuples (for edges).  However, 
             assigning a value to the "weight" attribute of an edge is done
             differently...
        * islands()
"""






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
