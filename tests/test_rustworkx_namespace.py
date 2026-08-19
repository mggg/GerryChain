"""GerryChain-specific checks for the relocated rustworkx compatibility namespace."""

import pickle

import pytest

import gerrychain.rustworkx as rustworkx
import gerrychain.rustworkx.rustworkx as extension


EXCEPTION_TYPES = [
    rustworkx.InvalidNode,
    rustworkx.DAGWouldCycle,
    rustworkx.NoEdgeBetweenNodes,
    rustworkx.DAGHasCycle,
    rustworkx.NoSuitableNeighbors,
    rustworkx.NullGraph,
    rustworkx.NoPathFound,
    rustworkx.InvalidMapping,
    rustworkx.JSONSerializationError,
    rustworkx.JSONDeserializationError,
    rustworkx.NegativeCycle,
    rustworkx.FailedToConverge,
    rustworkx.GraphNotBipartite,
]


def test_compatibility_versions_are_pinned():
    assert getattr(rustworkx, "__version__") == getattr(extension, "__version__") == "0.18.1"


@pytest.mark.parametrize("exception_type", EXCEPTION_TYPES)
def test_exception_uses_shipped_namespace_and_round_trips(exception_type: type[Exception]):
    assert exception_type.__module__ == "gerrychain.rustworkx"
    restored = pickle.loads(pickle.dumps(exception_type("message")))
    assert type(restored) is exception_type
    assert str(restored) == "message"
