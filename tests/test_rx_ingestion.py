"""Boundary tests for Graph.from_rustworkx() external-graph ingestion and detection.

The shipped-PyGraph path (identity embed, in-place normalization) is covered in
test_make_graph.py. This file exercises the runtime-only acceptance of graphs built with the
external rustworkx package, which is a test-only dependency pinned to 0.18.1: the copy must
preserve live indices exactly (including removal holes), share payloads by reference, stay
structurally independent, and never mutate the source; detection must never import rustworkx.
"""

import subprocess
import sys
import types
from typing import Any, cast

import pytest
import rustworkx as ext_rx

import gerrychain.rustworkx as shipped_rx
from gerrychain import Graph
from gerrychain.graph.graph import GraphValidationError


def _ingest_external(external: object) -> Graph:
    """Ingest an external graph; the cast documents that external acceptance is
    runtime-only and deliberately absent from the static signature."""
    return Graph.from_rustworkx(cast("shipped_rx.PyGraph[Any, Any]", external))


def _external_with_holes() -> "ext_rx.PyGraph":
    graph = ext_rx.PyGraph()
    graph.add_nodes_from([{"pop": i} for i in range(6)])
    graph.add_edges_from(
        [(0, 1, {"w": 1}), (1, 2, {"w": 2}), (2, 3, {"w": 3}), (3, 4, {"w": 4}), (4, 5, {"w": 5})]
    )
    graph.remove_node(3)  # leaves a node hole at 3 and edge holes at 2 and 3
    graph.attrs = {"source": "external"}
    return graph


def test_external_copy_preserves_indices_and_holes():
    external = _external_with_holes()
    wrapped = _ingest_external(external)
    copy = wrapped.get_rx_graph()

    assert type(copy) is shipped_rx.PyGraph
    assert copy is not external
    assert list(copy.node_indices()) == list(external.node_indices()) == [0, 1, 2, 4, 5]
    assert list(copy.edge_indices()) == list(external.edge_indices()) == [0, 1, 4]
    for edge_index in external.edge_indices():
        assert copy.get_edge_endpoints_by_index(edge_index) == external.get_edge_endpoints_by_index(
            edge_index
        )


def test_external_copy_shares_payloads_and_attrs_by_reference():
    external = _external_with_holes()
    copy = _ingest_external(external).get_rx_graph()

    for node_index in external.node_indices():
        assert copy.get_node_data(node_index) is external.get_node_data(node_index)
    for edge_index in external.edge_indices():
        assert copy.get_edge_data_by_index(edge_index) is external.get_edge_data_by_index(
            edge_index
        )
    assert copy.attrs is external.attrs


def test_external_copy_is_structurally_independent():
    external = _external_with_holes()
    copy = _ingest_external(external).get_rx_graph()

    new_in_copy = copy.add_node({"added": "copy"})
    assert new_in_copy not in set(external.node_indices())
    new_in_external = external.add_node({"added": "external"})
    assert new_in_external not in set(copy.node_indices())


def test_external_normalization_does_not_mutate_source():
    external = ext_rx.PyGraph()
    external.add_nodes_from([{}, {}])
    none_edge = external.add_edge(0, 1, None)

    copy = _ingest_external(external).get_rx_graph()

    assert copy.get_edge_data_by_index(none_edge) == {}
    assert external.get_edge_data_by_index(none_edge) is None


def test_external_multigraph_and_parallel_edges_preserved():
    for multigraph in (True, False):
        external = ext_rx.PyGraph(multigraph=multigraph)
        external.add_nodes_from([{}, {}])
        external.add_edge(0, 1, {"first": True})
        if multigraph:
            external.add_edge(0, 1, {"second": True})
        copy = _ingest_external(external).get_rx_graph()
        assert copy.multigraph == multigraph
        assert copy.num_edges() == external.num_edges()


def test_external_subgraph_ingests():
    external = _external_with_holes()
    sub = external.subgraph([0, 1, 2])
    copy = _ingest_external(sub).get_rx_graph()
    assert copy.num_nodes() == 3


def test_external_malformed_node_payload_rejected():
    external = ext_rx.PyGraph()
    external.add_node("not-a-dict")
    with pytest.raises(Exception, match="node_data dictionary"):
        _ingest_external(external)


def test_empty_graph_current_behavior_is_an_error():
    # Pins pre-existing behavior, unchanged by the backing-graph switch: from_rustworkx()
    # requires node index 0 to exist (it probes it for the __networkx_node__ mapping), so an
    # empty graph raises. from_null_networkx() is the supported empty-graph entry point.
    with pytest.raises(IndexError):
        Graph.from_rustworkx(shipped_rx.PyGraph())
    with pytest.raises(IndexError):
        _ingest_external(ext_rx.PyGraph())


def test_unsupported_external_version_rejected(monkeypatch: pytest.MonkeyPatch):
    external = _external_with_holes()
    monkeypatch.setattr(ext_rx, "__version__", "0.19.0")
    with pytest.raises(GraphValidationError, match="0.18.1"):
        _ingest_external(external)


def test_lookalike_and_directed_inputs_rejected():
    with pytest.raises(GraphValidationError, match="undirected"):
        _ingest_external(object())
    with pytest.raises(GraphValidationError, match="undirected"):
        _ingest_external(ext_rx.PyDiGraph())
    with pytest.raises(GraphValidationError, match="undirected"):
        Graph.from_rustworkx(shipped_rx.PyDiGraph())


@pytest.mark.parametrize("with_pygraph", [False, True])
def test_lookalike_rustworkx_module_rejected(monkeypatch: pytest.MonkeyPatch, with_pygraph: bool):
    lookalike = types.ModuleType("rustworkx")
    setattr(lookalike, "__version__", "0.18.1")
    if with_pygraph:

        class PyGraph:
            pass

        setattr(lookalike, "PyGraph", PyGraph)
        candidate: object = PyGraph()
    else:
        candidate = object()
    monkeypatch.setitem(sys.modules, "rustworkx", lookalike)

    with pytest.raises(GraphValidationError, match="undirected"):
        _ingest_external(candidate)


def test_shipped_ingestion_never_imports_external_rustworkx():
    # In a fresh interpreter, importing gerrychain and ingesting a shipped graph must leave
    # the external "rustworkx" module unimported; detection relies on sys.modules only.
    script = (
        "import sys\n"
        "import gerrychain.rustworkx as grx\n"
        "from gerrychain import Graph\n"
        "g = grx.PyGraph()\n"
        "g.add_nodes_from([{'a': 1}, {'a': 2}])\n"
        "g.add_edge(0, 1, {})\n"
        "wrapped = Graph.from_rustworkx(g)\n"
        "assert wrapped.get_rx_graph() is g\n"
        "assert 'rustworkx' not in sys.modules, 'external rustworkx was imported'\n"
        "try:\n"
        "    Graph.from_rustworkx(object())\n"
        "except Exception:\n"
        "    pass\n"
        "assert 'rustworkx' not in sys.modules, 'rejection path imported rustworkx'\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "OK"
