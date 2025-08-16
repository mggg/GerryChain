#
# This tests whether the routine, to_networkx_graph(), works
# properly.
#
# This routine extracts a new NetworkX.Graph object from an
# Graph object that is based on RustworkX.  When we create
# a Partition object from an NetworkX Graph we convert the
# graph to RustworkX for performance.  However, users might
# want to have access to a NetworkX Graph for a variety of
# reasons: mostly because they built their initial graph as
# a NetworkX Graph and they used node_ids that made sense to
# them at the time and would like to access the graph at
# the end of a MarkovChain run using those same "original"
# IDs.
# 
# The extracted NetworkX Graph should have the "original"
# node_ids, and it should have all of the node and edge
# data that was in the RustworkX Graph object.
#


import networkx as nx

from gerrychain.graph import Graph
from gerrychain.partition import Partition

def test_to_networkx_graph_works():

    """
    Create an NX graph (grid) that looks like this:

    'A' 'B' 'C'
    'D' 'E' 'F'
    'G' 'H' 'I'
    """

    nx_graph = nx.Graph()
    nx_graph.add_edges_from(
        [
            ('A', 'B'),
            ('A', 'D'),
            ('B', 'C'),
            ('B', 'E'),
            ('C', 'F'),
            ('D', 'E'),
            ('D', 'G'),
            ('E', 'F'),
            ('E', 'H'),
            ('F', 'I'),
            ('G', 'H'),
            ('H', 'I'),
        ]
    )

    # Add some node and edge data to the nx_graph

    graph_node_ids = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
    for node_id in graph_node_ids:
        nx_graph.nodes[node_id]["nx-node-data"] = node_id

    nx_graph.edges[('A','B')]["nx-edge-data"] = ('A','B')
    nx_graph.edges[('A','D')]["nx-edge-data"] = ('A','D')
    nx_graph.edges[('B','C')]["nx-edge-data"] = ('B','C')
    nx_graph.edges[('B','E')]["nx-edge-data"] = ('B','E')
    nx_graph.edges[('C','F')]["nx-edge-data"] = ('C','F')
    nx_graph.edges[('D','E')]["nx-edge-data"] = ('D','E')
    nx_graph.edges[('D','G')]["nx-edge-data"] = ('D','G')
    nx_graph.edges[('E','F')]["nx-edge-data"] = ('E','F')
    nx_graph.edges[('E','H')]["nx-edge-data"] = ('E','H')
    nx_graph.edges[('F','I')]["nx-edge-data"] = ('F','I')
    nx_graph.edges[('G','H')]["nx-edge-data"] = ('G','H')
    nx_graph.edges[('H','I')]["nx-edge-data"] = ('H','I')

    graph =  Graph.from_networkx(nx_graph)

    """
    Create a partition assigning each "row" of 
    nodes to a part (district), so the assignment
    looks like:

    0 0 0
    1 1 1
    2 2 2
    """

    initial_assignment = {
     'A': 0,
     'B': 0,
     'C': 0,
     'D': 1,
     'E': 1,
     'F': 1,
     'G': 2,
     'H': 2,
     'I': 2,
    }

    # Create a partition
    partition = Partition(graph, initial_assignment)

    # The partition's graph object has been converted to be based on RX
    new_graph = partition.graph

    # Add some additional data
    for node_id in new_graph.node_indices:
        new_graph.node_data(node_id)["internal-node-data"] = new_graph.original_node_id_for_internal_node_id(node_id)
    for edge_id in new_graph.edge_indices:
        new_graph.edge_data(edge_id)["internal-edge-data"] = "internal-edge-data"

    # Now create a second partition by flipping the 
    # nodes in the first row to be in part (district) 1

    """
    The new partition's mapping of nodes to parts should look like this:

    1 1 1
    1 1 1
    2 2 2
    """

    flips = {'A': 1, 'B': 1, 'C': 1}
    # Create a new partition based on these flips - using "original" node_ids
    new_partition = partition.flip(flips, use_original_node_ids=True)


    # Get the NX graph after doing the flips.
    extracted_nx_graph = new_partition.graph.to_networkx_graph()

    # Get the assignments for both the initial partition and the new_partition

    internal_assignment_0 = partition.assignment
    internal_assignment_1 = new_partition.assignment

    # convert the internal assignments into "original" node_ids
    original_assignment_0 = {}
    for node_id, part in internal_assignment_0.items():
        original_node_id = partition.graph.original_node_id_for_internal_node_id(node_id)
        original_assignment_0[original_node_id] = part
    original_assignment_1 = {}
    for node_id, part in internal_assignment_1.items():
        original_node_id = partition.graph.original_node_id_for_internal_node_id(node_id)
        original_assignment_1[original_node_id] = part

    # Check that all is well...

    # Check that the initial assignment is the same as the internal RX-based assignment
    for node_id, part in initial_assignment.items():
        assert (part == original_assignment_0[node_id])

    # Check that the flips did what they were supposed to do
    for node_id in ['A', 'B', 'C', 'D', 'E', 'F']:
        assert(original_assignment_1[node_id] == 1)
    for node_id in ['G', 'H', 'I']:
        assert(original_assignment_1[node_id] == 2)

    # Check that the node and edge data is present

    # Check node data
    for node_id in extracted_nx_graph.nodes:
        # Data assigned to the NX-Graph should still be there...
        assert(
          extracted_nx_graph.nodes[node_id]["nx-node-data"] 
          == 
          nx_graph.nodes[node_id]["nx-node-data"] 
        )
        # Data assigned to the partition's RX-Graph should still be there...
        assert(
          extracted_nx_graph.nodes[node_id]["internal-node-data"] 
          == 
          node_id
        )
        # Node_id agrees with __networkx_node__ (created by RX conversion)
        assert(
          node_id
          == 
          extracted_nx_graph.nodes[node_id]["__networkx_node__"] 
        )


    # Check edge data 
    for edge in extracted_nx_graph.edges:
        assert(
          extracted_nx_graph.edges[edge]["nx-edge-data"] 
          == 
          nx_graph.edges[edge]["nx-edge-data"] 
        )
        # Data assigned to the partition's RX-Graph should still be there...
        assert(
          extracted_nx_graph.edges[edge]["internal-edge-data"] 
          == 
          "internal-edge-data"
        )
    # compare the extracted_nx_graph's nodes and edges to see if they make sense
    # Compare node_data and edge_data

