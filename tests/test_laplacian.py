import random
from typing import Any, cast

import networkx as nx
import numpy as np
import numpy.typing as npt
import pytest
import gerrychain.rustworkx as rx
import scipy.sparse

from gerrychain.graph import Graph

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


def _dense(matrix: "scipy.sparse.sparray | scipy.sparse.spmatrix | npt.NDArray[Any]"):
    """Return a dense float ndarray for a scipy sparse array/matrix (or ndarray)."""
    # cast: pyright does not narrow the union on the hasattr check
    dense = cast(scipy.sparse.csr_array, matrix).todense() if hasattr(matrix, "todense") else matrix
    return np.asarray(dense, dtype=float)


def are_sparse_matrices_equal(
    sparse_matrix1: scipy.sparse.csr_array,
    sparse_matrix2: scipy.sparse.csr_array,
    rtol: float = 1e-05,
    atol: float = 1e-08,
):
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
    if not (
        np.array_equal(sparse_matrix1.indices, sparse_matrix2.indices)
        and np.array_equal(sparse_matrix1.indptr, sparse_matrix2.indptr)
    ):
        return False

    # Check for approximate equality of data (values)
    # Use np.allclose to handle floating-point comparisons
    if not np.allclose(sparse_matrix1.data, sparse_matrix2.data, rtol=rtol, atol=atol):
        return False

    return True


# Create equivalent NX and RX graphs from scratch


@pytest.fixture
def nx_graph() -> "nx.Graph[int, dict[str, Any], dict[str, Any]]":
    this_nx_graph: "nx.Graph[int, dict[str, Any], dict[str, Any]]" = nx.Graph(
        [(0, 1), (0, 2), (1, 2), (2, 3)]
    )
    return this_nx_graph


@pytest.fixture
def rx_graph() -> "rx.PyGraph[dict[str, Any], dict[str, Any]]":
    this_rx_graph: "rx.PyGraph[dict[str, Any], dict[str, Any]]" = rx.PyGraph()
    # argument to add_node_from() is the data to be associated with each node.
    # To be compatible with GerryChain, nodes need to have data values that are dictionaries
    # so we just have an empty dict for each node's data
    this_rx_graph.add_nodes_from([{}, {}, {}, {}])
    this_rx_graph.add_edges_from([(0, 1, {}), (0, 2, {}), (1, 2, {}), (2, 3, {})])
    return this_rx_graph


def test_nx_rx_laplacian_matrix_equality(
    nx_graph: "nx.Graph[int, dict[str, Any], dict[str, Any]]",
    rx_graph: "rx.PyGraph[dict[str, Any], dict[str, Any]]",
):
    # Create Graph objects from the NX and RX graphs
    gc_nx_graph = Graph.from_networkx(nx_graph)
    gc_rx_graph = Graph.from_rustworkx(rx_graph)

    # Compute the laplacian_matrix for both the NX and RX based Graph objects
    gc_nx_laplacian_matrix = gc_nx_graph.laplacian_matrix()
    gc_rx_laplacian_matrix = gc_rx_graph.laplacian_matrix()

    # Convert values in the NX version to be floating point
    float_gc_nx_laplacian_matrix = gc_nx_laplacian_matrix.astype(float)

    # test equality
    matrices_are_equal = are_sparse_matrices_equal(
        float_gc_nx_laplacian_matrix, gc_rx_laplacian_matrix
    )
    assert matrices_are_equal


def _random_connected_graph_edges(num_nodes: int, rng: random.Random) -> list[tuple[int, int]]:
    """Return a sorted edge list for a random connected graph on nodes ``0..num_nodes-1``.

    Builds a random spanning tree (which guarantees connectivity) by attaching each new node
    to a random earlier one, then adds a random number of extra edges to introduce cycles and
    varied degrees.
    """
    edges = set()

    # Random spanning tree: every node 1..n-1 links back to an earlier node.
    for node in range(1, num_nodes):
        parent = rng.randrange(node)
        edges.add((parent, node))

    # Extra edges to create cycles / a range of degrees.
    for _ in range(rng.randint(0, num_nodes)):
        u, v = rng.randrange(num_nodes), rng.randrange(num_nodes)
        if u != v:
            edges.add((min(u, v), max(u, v)))
    return sorted(edges)


RANDOM_GRAPH_CASES = [
    (num_nodes, seed) for num_nodes in (2, 3, 5, 8, 16, 32, 64) for seed in range(4)
]


@pytest.mark.parametrize("num_nodes, seed", RANDOM_GRAPH_CASES)
def test_rx_normalized_laplacian_matches_networkx_reference(num_nodes: int, seed: int):
    # networkx.normalized_laplacian_matrix() is the reference implementation (and the one
    # the NX path delegates to). The RX path computes the normalized Laplacian by hand, so
    # it must agree with the reference across a range of randomized, connected graphs.
    edges = _random_connected_graph_edges(num_nodes, random.Random(seed))

    nx_graph = nx.Graph()
    nx_graph.add_nodes_from(range(num_nodes))
    nx_graph.add_edges_from(edges)
    assert nx.is_connected(nx_graph)  # sanity-check the generator

    rx_graph = rx.PyGraph()
    rx_graph.add_nodes_from([{} for _ in range(num_nodes)])
    rx_graph.add_edges_from([(u, v, {}) for u, v in edges])

    # Build both matrices over the same node ordering (0..num_nodes-1) so they are comparable.
    reference = _dense(nx.normalized_laplacian_matrix(nx_graph, nodelist=list(range(num_nodes))))
    rx_result = _dense(Graph.from_rustworkx(rx_graph).normalized_laplacian_matrix())

    assert rx_result.shape == reference.shape
    assert np.allclose(rx_result, reference)
    assert np.allclose(rx_result, rx_result.T)  # undirected => symmetric


def test_normalized_laplacian_is_symmetric(rx_graph: "rx.PyGraph[dict[str, Any], dict[str, Any]]"):
    gc_rx_graph = Graph.from_rustworkx(rx_graph)
    rx_result = _dense(gc_rx_graph.normalized_laplacian_matrix())

    assert np.allclose(rx_result, rx_result.T)


def test_normalized_laplacian_with_isolated_node():
    # Node 3 is isolated (degree 0). The normalization divides by sqrt(degree), so this exercises
    # the divide-by-zero guard (inf -> 0) and makes sure an all-zero row/column is produced for
    # the isolated node rather than NaNs.
    edges = [(0, 1), (1, 2)]
    num_nodes = 4

    nx_graph = nx.Graph()
    nx_graph.add_nodes_from(range(num_nodes))
    nx_graph.add_edges_from(edges)
    reference = _dense(nx.normalized_laplacian_matrix(nx_graph, nodelist=list(range(num_nodes))))

    rx_graph = rx.PyGraph()
    rx_graph.add_nodes_from([{} for _ in range(num_nodes)])
    rx_graph.add_edges_from([(u, v, {}) for u, v in edges])
    rx_result = _dense(Graph.from_rustworkx(rx_graph).normalized_laplacian_matrix())

    assert np.allclose(rx_result, reference)
    assert not np.isnan(rx_result).any()
    assert np.allclose(rx_result[3, :], 0.0)
    assert np.allclose(rx_result[:, 3], 0.0)
