
import pytest
import networkx as nx
import rustworkx as rx
import numpy as np
from gerrychain.graph import Graph
import gerrychain.tree as gctree

"""
This tests whether we compute the same laplacian matrix for NX and RX
based Graph objects.

The NX version is computed (as was true in the old code) by a built-in
NetworkX routine.  The RX version is computed by code added when we 
supported RX as the embedded graph object.

The NX version produces ints from the code below, while the RX 
version produces floats.  I don't think this matters as the laplacian
matrix is used to do numerical calculations, so that code should 
happily use ints or floats, but it means that for this test I need
to convert the NX version's result to have floating point values.
"""

# frm: TODO:  Add additional tests for laplacian matrix calculations, in 
#             particular, add a test for normalized_laplacian_matrix()
#             once that routine has been implemented.


def are_sparse_matrices_equal(sparse_matrix1, sparse_matrix2, rtol=1e-05, atol=1e-08):
    """
    Checks if two scipy.sparse.csr_matrix objects are equal, considering
    potential floating-point inaccuracies in the data.

    Args:
        sparse_matrix1 (scipy.sparse.csr_matrix): The first sparse matrix.
        sparse_matrix2 (scipy.sparse.csr_matrix): The second sparse matrix.
        rtol (float): The relative tolerance parameter for np.allclose.
        atol (float): The absolute tolerance parameter for np.allclose.

    Returns:
        bool: True if the sparse matrices are equal, False otherwise.
    """
    # Check if shapes are equal
    if sparse_matrix1.shape != sparse_matrix2.shape:
        return False

    # Check if the number of non-zero elements is equal
    if sparse_matrix1.nnz != sparse_matrix2.nnz:
        return False

    # Check for equality of structural components (indices and indptr)
    # These should be exact matches
    if not (np.array_equal(sparse_matrix1.indices, sparse_matrix2.indices) and
            np.array_equal(sparse_matrix1.indptr, sparse_matrix2.indptr)):
        return False

    # Check for approximate equality of data (values)
    # Use np.allclose to handle floating-point comparisons
    if not np.allclose(sparse_matrix1.data, sparse_matrix2.data, rtol=rtol, atol=atol):
        return False

    return True

# Create equivalent NX and RX graphs from scratch

@pytest.fixture
def nx_graph():
    this_nx_graph = nx.Graph([(0, 1), (0, 2), (1, 2), (2, 3)])
    return this_nx_graph

@pytest.fixture
def rx_graph():
    this_rx_graph = rx.PyGraph()
    this_rx_graph.add_nodes_from([0, 1, 2, 3])
    this_rx_graph.add_edges_from([(0, 1, "data"), (0, 2, "data"), (1, 2, "data"), (2, 3, "data")])
    return this_rx_graph


def test_nx_rx_laplacian_matrix_equality(nx_graph, rx_graph):

    # Create Graph objects from the NX and RX graphs
    gc_nx_graph = Graph.from_networkx(nx_graph)
    gc_rx_graph = Graph.from_rustworkx(rx_graph)

    # Compute the laplacian_matrix for both the NX and RX based Graph objects
    gc_nx_laplacian_matrix = gc_nx_graph.laplacian_matrix()
    gc_rx_laplacian_matrix = gc_rx_graph.laplacian_matrix()

    # Convert values in the NX version to be floating point
    float_gc_nx_laplacian_matrix = gc_nx_laplacian_matrix.astype(float)

    # test equality
    matrices_are_equal = are_sparse_matrices_equal(float_gc_nx_laplacian_matrix, gc_rx_laplacian_matrix)
    assert(matrices_are_equal)

