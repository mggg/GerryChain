
import networkx as nx
import rustworkx as rx
import numpy as np
from graph import Graph
import tree as gc_tree

# Create an RX graph (replace with your graph data)
rx_graph = rx.PyGraph()
rx_graph.add_nodes_from([0, 1, 2, 3])
rx_graph.add_edges_from([(0, 1, "data"), (0, 2, "data"), (1, 2, "data"), (2, 3, "data")])

# 1. Get the adjacency matrix
adj_matrix = rx.adjacency_matrix(rx_graph)

# 2. Calculate the degree matrix (simplified for this example)
degree_matrix = np.diag([rx_graph.degree(node) for node in rx_graph.node_indices()])

# 3. Calculate the Laplacian matrix
rx_laplacian_matrix = degree_matrix - adj_matrix

print("RX Adjacency Matrix:")
print(adj_matrix)

print("\nRX Degree Matrix:")
print(degree_matrix)

print("\nRX Laplacian Matrix:")
print(rx_laplacian_matrix)

print("type of RX laplacian_matrix is: ", type(rx_laplacian_matrix))

# Create an NX graph (replace with your graph data)
nx_graph = nx.Graph([(0, 1), (0, 2), (1, 2), (2, 3)])
nx_laplacian_matrix = nx.laplacian_matrix(nx_graph)

print("\nNX Laplacian Matrix:")
print(nx_laplacian_matrix)

print("type of NX laplacian_matrix is: ", type(nx_laplacian_matrix))

gc_nx_graph = Graph.from_nx_graph(nx_graph)
gc_rx_graph = Graph.from_rx_graph(rx_graph)

print("\ngc_laplacian(nx_graph) is: ", gctree.gc_laplacian_matrix(gc_nx_graph))
print("\ngc_laplacian(rx_graph) is: ", gctree.gc_laplacian_matrix(gc_rx_graph))
