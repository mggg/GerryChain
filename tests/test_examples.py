"""Tests for the bundled example graphs in :mod:`gerrychain.examples`."""

import pathlib

import pytest

from gerrychain import Graph
from gerrychain.examples import gerrymandria


def test_gerrymandria_loads():
    graph = gerrymandria()
    assert isinstance(graph, Graph)
    assert len(graph.nodes) == 64  # 8x8 grid
    assert len(graph.edges) == 112  # 2 * 8 * 7 grid edges


def test_gerrymandria_has_region_attributes():
    graph = gerrymandria()
    for attr in ("county", "muni", "water_dist", "TOTPOP", "district", "x", "y"):
        # every node carries the attribute
        for node_id in graph.node_indices:
            assert attr in graph.node_data(node_id)
    assert sorted({graph.node_data(n)["county"] for n in graph.node_indices}) == [
        "1",
        "2",
        "3",
        "4",
    ]


def test_gerrymandria_is_self_contained(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    # The point of shipping the data with the package is that it loads regardless of the working
    # directory (unlike the old Graph.from_json("./gerrymandria.json") relative-path loading).
    monkeypatch.chdir(tmp_path)
    graph = gerrymandria()
    assert len(graph.nodes) == 64
