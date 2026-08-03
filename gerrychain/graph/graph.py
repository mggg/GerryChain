"""
This module provides tools for working with graphs in the context of geographic data.

It defines a Graph class (similar in many ways to NetworkX.Graph) with standard
graph functionality along with some GerryChain specific functionality.

It defines a FrozenGraph class which makes a Graph immutable in order to speed
up operations on the graph once the graph has been created (and no additional nodes
or edges will be added to the graph).

It also defines some utility functions to manage external data.

This module is designed to be used in conjunction with geopandas, shapely, and pandas libraries,
facilitating the integration of graph-based algorithms with geographic information systems (GIS).

Note:
This module relies on NetworkX, RustworkX, pandas, and geopandas, which should be installed and
imported as required.

"""

from __future__ import annotations

import functools
import json
import warnings
from collections.abc import Generator, Hashable, Iterable, Iterator, Mapping, Sequence
from collections.abc import Set as AbstractSet

# frm: codereview note: removed type hints that are now baked into Python
from typing import Any, Protocol, TypedDict, TypeVar, cast

import geopandas as gp
import networkx
import numpy
import pandas as pd
import rustworkx
import scipy
from networkx.readwrite import json_graph
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.prepared import prep

from .._config import runtime_checks_enabled
from .adjacency import neighbors
from .geo import GeometryError, invalid_geometries, reprojected


class _AdjacencyData(TypedDict):
    nodes: list[dict[str, object]]


class _GeoInterface(Protocol):
    __geo_interface__: dict[str, object]


_AttributeDict = dict[str, Any]
_NodeT = TypeVar("_NodeT", bound=Hashable)
_NodeDataT = TypeVar("_NodeDataT", bound=_AttributeDict)
_EdgeDataT = TypeVar("_EdgeDataT", bound=_AttributeDict)


class GraphValidationError(Exception):
    """Raised when a Graph fails an integrity check (see ``verify_graph_is_valid``)."""


class _NodeCollection(list[Hashable]):
    def __call__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "As of GerryChain version 1.0.0, `Graph.nodes` is a property, not a method. Use "
            "`graph.nodes` without parentheses; use `graph.node_data(node_id)` for node attributes."
        )


class _EdgeCollection(set[tuple[Hashable, Hashable]]):
    def __call__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "As of GerryChain version 1.0.0, `Graph.edges` is a property, not a method. Use "
            "`graph.edges` without parentheses; use `graph.edge_data(edge_id)` for edge attributes."
        )


def json_serialize(input_object: object) -> int | None:
    """Return converted pandas object or None if input is not of type pd.Int64Dtype.

    This function is used to handle one of the common issues that appears when trying to convert a
    pandas dataframe into a JSON serializable object.

    Specifically, it handles the issue of converting the pandas int64 to a python int so that JSON
    can serialize it and so that we can write graphs out to JSON files.

    Args:
        input_object (object): An object expected to be a NumPy integer.

    Returns:
        int | None: The converted pandas object or None if input is not of type pd.Int64Dtype
    """
    if isinstance(input_object, numpy.integer):
        return int(input_object)

    return None


class Graph:
    """
    This class closely mirrors the interface of a NetworkX Graph object, but with
    additions specific to GerryChain.  It was created initially to represent geographical
    data (such as voting precincts) that would support the creation of voting district
    plans, but it can be used for general graph operations.  For a more detailed
    description of the kinds of operations this class supports, please refer to
    the NetworkX documentation (https://networkx.org/documentation/stable/)

    Note that this class encapsulates / wraps an underlying graph object which can either be a
    NetworkX graph or a RustworkX graph.  The intent is that this class provides the same
    external interface as a NetworkX graph (for all of the uses that GerryChain cares
    about, at least) so that legacy GerryChain code that operated on NetworkX based Graph objects
    can mostly continue to work unchanged.

    When a graph is added to a partition, however, the NX graph will be converted into
    an RX graph and the NX graph will become inaccessible to the user.  The RX graph
    may also be "frozen" the way the NX graph was "frozen" in the legacy code, but we
    have not yet gotten that far in the implementation.

    The reason for converting to an underlying RX graph is to gain the performance
    gains of the RustworkX library vis-a-vis NetworkX.  The reason to continue to
    support NetworkX is because NetworkX has many user-friendly convenience functions
    that a user might want to use to create a graph.

    So, the usage paradigm is to create a graph using NetworkX and to then convert
    to RustworkX for the compute intensive work done by MarkovChain().

    Note that the conversion from NX to RX is done automatically when the user
    creates a Partition object.
    """

    # Note: This class deliberately has no __init__. Some non-GerryChain code (e.g.
    #       rustworkx's networkx_converter) constructs Graph instances via the default
    #       constructor, ``cls()``, and the ``from_*`` classmethods rely on that too -
    #       they do ``graph = cls()`` and then populate the backing graph.
    #
    #       Instead of a constructor we give the two backing-graph fields class-level
    #       defaults of None. This guarantees ``self._nx_graph`` / ``self._rx_graph``
    #       always resolve (even on a bare ``Graph()``), so ``is_nx_graph()`` /
    #       ``is_rx_graph()`` can test them directly without ever triggering attribute
    #       fallback. A bare, unconfigured Graph therefore has both set to None, which
    #       ``verify_graph_is_valid()`` reports as a clear error.
    _nx_graph: networkx.Graph[Hashable, _AttributeDict, _AttributeDict] | None = None
    _rx_graph: rustworkx.PyGraph[_AttributeDict, _AttributeDict] | None = None
    _is_a_subgraph = False
    _node_id_to_parent_node_id_map: dict[Hashable, Hashable] = {}
    _node_id_to_original_nx_node_id_map: dict[Hashable, Hashable] = {}
    nx_to_rx_node_id_map: dict[Hashable, Hashable] | None = None
    # Canonical node order for NX subgraphs; None for top-level and RX graphs. Needed for
    # reproducible subgraph creation, since string hashing there can still be off.
    _nx_node_order: list[Hashable] | None = None

    @classmethod
    def from_networkx(cls, nx_graph: networkx.Graph[_NodeT, _NodeDataT, _EdgeDataT]) -> Graph:
        """Create a Graph from a NetworkX.Graph object.

        This supports the use case of users creating a graph using NetworkX which is convenient -
        both for users of the previous implementation of a GerryChain object which was a subclass
        of NetworkX.Graph and for users more generally who are familiar with NetworkX.

        Note that most users will not ever call this function directly, because they can create a
        GerryChain Partition object directly from a NetworkX graph, and the Partition
        initialization code will use this function to convert the NetworkX graph to a GerryChain
        Graph object.

        Args:
            nx_graph (networkx.Graph): A NetworkX.Graph object with node and edge data to be
                converted into a GerryChain Graph object.

        Returns:
            Graph: A Graph object embedding the given NetworkX Graph
        """
        if nx_graph.is_directed():
            raise GraphValidationError(
                "GerryChain Graph objects must be undirected; "
                "Graph.from_networkx() received a directed graph."
            )

        graph = cls()
        graph._nx_graph = cast("networkx.Graph[Hashable, _AttributeDict, _AttributeDict]", nx_graph)
        graph._rx_graph = None
        graph._is_a_subgraph = False  # See comments on RX subgraph issues.
        # Maps node_ids in the graph to the "parent" node_ids in the parent graph.
        # For top-level graphs, this is just an identity map
        graph._node_id_to_parent_node_id_map = {node_id: node_id for node_id in graph.node_indices}
        # Maps node_ids in the graph to the "original" node_ids in parent graph.
        # For top-level graphs, this is just an identity map
        graph._node_id_to_original_nx_node_id_map = {
            node_id: node_id for node_id in graph.node_indices
        }
        graph.nx_to_rx_node_id_map = (
            None  # only set when an NX based graph is converted to be an RX based graph
        )
        graph.verify_graph_is_valid()
        return graph

    @classmethod
    def from_null_networkx(cls) -> Graph:
        """Create a Graph that has an empty embedded NetworkX Graph.

        This was originally implemented as a way to encapsulate NetworkX dependencies in GerryChain
        code to this module (graph.py).

        It supports the use case of a user who wants to build a graph from scratch without
        reference to NetworkX.

        Returns:
            Graph: A Graph object with no nodes
        """

        nx_graph: networkx.Graph[Hashable, _AttributeDict, _AttributeDict] = networkx.Graph()
        return Graph.from_networkx(nx_graph)

    @classmethod
    def from_rustworkx(
        cls, rx_graph: rustworkx.PyGraph[_NodeDataT, Any] | rustworkx.PyDiGraph[_NodeDataT, Any]
    ) -> Graph:
        """Create a Graph from a RustworkX.PyGraph object.

        There are three primary use cases for this routine: 1) converting an NX-based Graph to be
        an RX-based Graph, 2) creating a subgraph of an RX-based Graph, and 3) creating a Graph
        whose node_ids do not need to be mapped to some previous graph's node_ids.

        In a little more detail:

        1) A typical way to use GerryChain is to create a graph using NetworkX functionality and to
        then rely on the initialization code in the Partition class to create an RX-based Graph
        object. That initialization code constructs a RustworkX PyGraph and then uses this routine
        to create an RX-based Graph object, and it then creates maps from the node_ids of the
        resulting RX-based Graph back to the original NetworkX.Graph's node_ids.

        2) When creating a subgraph of a RustworkX PyGraph object, the node_ids of the subgraph are
        (in general) different from those of the parent graph. So we create a mapping from the
        subgraph's node_ids to the node_ids of the parent. The subgraph() routine creates a
        RustworkX PyGraph subgraph, then uses this routine to create an RX-based Graph using that
        subgraph, and it then creates the mapping of subgraph node_ids to the parent (RX) graph's
        node_ids.

        3) In those cases where no node_id mapping is needed this routine provides a simple way to
        create an RX-based GerryChain graph object.

        Args:
            rx_graph (rustworkx.PyGraph | rustworkx.PyDiGraph): a RustworkX graph object. A
                directed ``PyDiGraph`` is rejected with :class:`GraphValidationError`.

        Returns:
            'Graph': a GerryChain Graph object with an embedded RustworkX.PyGraph object
        """
        if not isinstance(rx_graph, rustworkx.PyGraph):
            raise GraphValidationError(
                "GerryChain Graph objects must be undirected; "
                "Graph.from_rustworkx() requires a rustworkx.PyGraph."
            )

        # Ensure that the RX graph has node and edge data dictionaries
        #
        # While NX graphs always have node and edge data dictionaries,
        # the node data for the nodes in RX graphs do not have to be
        # a data dictionary - they can be any Python object.  Since
        # gerrychain code depends on having a data dictionary
        # associated with nodes and edges, we need to check the RX
        # graph to see if it already has node and edge data and if so,
        # whether that node and edge data is a data dictionary.
        #
        # Note that there is no way to change the type of the data
        # associated with an RX node.  So if the data for a node
        # is not already a dict then we have an unrecoverable error.
        #
        # However, RX does allow you to update the data for edges,
        # so if we find an edge with no data (None), then we can
        # create an empty dict for the edge data, and if the edge
        # data is some other type, then we can also replace the
        # existing edge data with a dict (retaining the original
        # data as a value in the new dict)

        graph = cls()
        for node_id in rx_graph.node_indices():
            data_dict = rx_graph[node_id]
            if not isinstance(data_dict, dict):
                # Unrecoverable error - see above...
                raise Exception(
                    "from_rustworkx(): RustworkX graph does not have node_data dictionary"
                )

        for edge_id in rx_graph.edge_indices():
            data_dict = rx_graph.get_edge_data_by_index(edge_id)
            if data_dict is None:
                # Create an empty dict for edge_data
                graph.update_edge_by_index(edge_id, {})
            if not isinstance(data_dict, dict):
                # Create a new dict with the existing edge_data as an item
                graph.update_edge_by_index(edge_id, {"__original_rx_edge_data": data_dict})

        graph = cls()
        graph._rx_graph = cast(rustworkx.PyGraph[_AttributeDict, _AttributeDict], rx_graph)
        graph._nx_graph = None
        graph._is_a_subgraph = False  # See comments on RX subgraph issues.

        # At this point, we don't know whether the graph is derived from NX, is a
        # subgraph, or is something that can stand alone, so we just create
        # the maps (dicts) that map RX node_ids to other node_ids that are
        # identity maps (each node_id is mapped to itself).
        #
        # It is responsibility of callers to reset the maps if that is appropriate...

        graph._node_id_to_parent_node_id_map = {node_id: node_id for node_id in graph.node_indices}

        """ frm: TODO: Debugging: Delete this comment
         - need to decide if I should check to see if there is already node_data
           for the original nx node id, in the case when we create an RX spanning tree...
           That is - we sometimes use this function for graphs that we create internally
           that may already have node data that we want to preserve...
        """

        # Retain original NX node_ids if they exist.
        #
        # When we create a spanning tree, we create a Graph from an RX graph, but in that case
        # we have node_data from the "real" graph, so we should preserve the mapping
        # from internal RX node_ids to the original NX node_ids.
        #
        # So, check one node to see if it has an original NX node_id, and if so create
        # the map using that data, otherwise just create an identity map.
        #
        node_data_for_rx_node_id_0 = rx_graph.get_node_data(0)
        if "__networkx_node__" in node_data_for_rx_node_id_0:
            graph._node_id_to_original_nx_node_id_map = {
                node_id: graph.node_data(node_id)["__networkx_node__"]
                for node_id in graph.node_indices
            }
        else:
            graph._node_id_to_original_nx_node_id_map = {
                node_id: node_id for node_id in graph.node_indices
            }

        # only set when an NX based graph is converted to be an RX based graph
        graph.nx_to_rx_node_id_map = None

        graph.verify_graph_is_valid(thorough=False)

        return graph

    def to_networkx_graph(
        self,
    ) -> networkx.Graph[Hashable, _AttributeDict, _AttributeDict]:
        """Create a NetworkX.Graph object that has the same nodes, edges, node_data, and edge_data.
        as the GerryChain Graph object.

        The intended purpose of this routine is to allow a user to run a MarkovChain - which uses
        an embedded RustworkX graph and then extract an equivalent version of that graph with all
        of its data as a NetworkX.Graph object - in order to use NetworkX routines to access and
        manipulate the graph.

        In short, this routine allows users to use NetworkX functionality on a graph after running
        a MarkovChain.

        If the GerryChain graph object is NX-based, then this routine merely returns the embedded
        NetworkX.Graph object.

        Returns:
            networkx.Graph: A NetworkX.Graph object that is equivalent to the GerryChain Graph
                object (nodes, edges, node_data, edge_data)
        """
        if self._nx_graph is not None:
            return self.get_nx_graph()

        if self._rx_graph is None:
            raise TypeError("Graph passed to 'to_networkx_graph()' must be a rustworkx graph")

        # We have an RX-based Graph, and we want to create a NetworkX Graph object
        # that has all of the node data and edge data, and which has the
        # node_ids and edge_ids of the original NX graph.
        #
        # Original node_ids are those that were used in the original NX
        # Graph used to create the RX-based Graph object.
        #

        # Confirm that this RX based graph was derived from an NX graph...
        if self._node_id_to_original_nx_node_id_map is None:
            raise Exception("to_networkx_graph(): _node_id_to_original_nx_node_id_map is None")

        rx_graph = self.get_rx_graph()

        # Extract node data
        node_data = []
        for node_id in rx_graph.node_indices():
            node_payload = rx_graph[node_id]
            # Get the "original" node_id
            original_nx_node_id = self.original_nx_node_id_for_internal_node_id(node_id)
            node_data.append({"node_name": original_nx_node_id, **node_payload})

        # Extract edge data
        edge_data = []
        for edge_id in rx_graph.edge_indices():
            edge = rx_graph.get_edge_endpoints_by_index(edge_id)
            edge_0_node_id = edge[0]
            edge_1_node_id = edge[1]
            # Get the "original" node_ids
            edge_0_original_nx_node_id = self.original_nx_node_id_for_internal_node_id(
                edge_0_node_id
            )
            edge_1_original_nx_node_id = self.original_nx_node_id_for_internal_node_id(
                edge_1_node_id
            )
            edge_payload = rx_graph.get_edge_data_by_index(edge_id)
            # Add edges and edge data using the original node_ids
            # as the names/IDs for the nodes that make up the edge
            edge_data.append(
                {
                    "source": edge_0_original_nx_node_id,
                    "target": edge_1_original_nx_node_id,
                    **edge_payload,
                }
            )

        # Create Pandas DataFrames

        nodes_df = pd.DataFrame(node_data)
        edges_df = pd.DataFrame(edge_data)

        # Create a NetworkX Graph object from the edges_df, using
        # "source", and "tartet" to define edge node_ids, and adding
        # all attribute data (True).
        nx_graph = cast(
            "networkx.Graph[Hashable, _AttributeDict, _AttributeDict]",
            networkx.from_pandas_edgelist(
                edges_df, source="source", target="target", edge_attr=True
            ),
        )

        # Add all of the node_data, using the "node_name" attr as the NX Graph node_id
        nodes_df = nodes_df.set_index("node_name")
        networkx.set_node_attributes(nx_graph, nodes_df.to_dict(orient="index"))

        return nx_graph

    def original_nx_node_id_for_internal_node_id(self, internal_node_id: Hashable) -> Hashable:
        """Translate a node_id to its "original" node_id.

        Args:
            internal_node_id (Hashable): A node ID to translate.

        Returns:
            Hashable: The translated node ID.
        """
        return self._node_id_to_original_nx_node_id_map[internal_node_id]

    def original_nx_node_ids_for_set(self, set_of_node_ids: set[Hashable]) -> set[Hashable]:
        """Translate a set of node_ids to their "original" node_ids.

        Args:
            set_of_node_ids (set[Hashable]): Node IDs to translate.

        Returns:
            set[Hashable]: The translated node IDs.
        """
        _node_id_to_original_nx_node_id_map = self._node_id_to_original_nx_node_id_map
        new_set = {_node_id_to_original_nx_node_id_map[node_id] for node_id in set_of_node_ids}
        return new_set

    def original_nx_node_ids_for_list(self, list_of_node_ids: list[Hashable]) -> list[Hashable]:
        """Translate a list of node_ids to their "original" node_ids.


        Args:
            list_of_node_ids (list[Hashable]): Node IDs to translate.

        Returns:
            list[Hashable]: The translated node IDs.
        """
        # Utility routine to quickly translate a set of node_ids to their original node_ids
        _node_id_to_original_nx_node_id_map = self._node_id_to_original_nx_node_id_map
        new_list = [_node_id_to_original_nx_node_id_map[node_id] for node_id in list_of_node_ids]
        return new_list

    def internal_node_id_for_original_nx_node_id(self, original_nx_node_id: Hashable) -> Hashable:
        """Return corresponding "internal" node_id.

        Discover the "internal" node_id in the current GerryChain graph that corresponds to the
        "original" node_id in the top-level graph (presumably an NX-based graph object).

        This was originally created to facilitate testing where it was convenient to express the
        test success criteria in terms of "original" node_ids, but the actual test needed to be
        made using the "internal" (RX) node_ids.

        Args:
            original_nx_node_id (Hashable): The original node ID.

        Returns:
            Hashable: The corresponding internal node ID.
        """
        # Note: TODO: Performance: This code is inefficient but it is not a priority to fix now...
        #
        # The code reverses the dict that maps internal node_ids to "original"
        # node_ids, which has an entry for every node in the graph - hence large
        # for large graphs, which is costly, but worse - it does this every time
        # it is called, so if the calling code is looping through a list of nodes
        # then this reverse dict computation will happen each time.
        #
        # The obvious fix is to just create the reverse map once when the "internal"
        # graph is created.  This would be simple to do and safe, because the
        # "internal" graph is frozen.
        #
        # However, at present (December 2025) this routine is only ever used for
        # tests, so I am putting it on the back burner...

        # reverse the map so we can go from original node_id to internal node_id
        orignal_node_id_to_internal_node_id_map = {
            v: k for k, v in self._node_id_to_original_nx_node_id_map.items()
        }
        return orignal_node_id_to_internal_node_id_map[original_nx_node_id]

    def verify_graph_is_valid(self, thorough: bool | None = None) -> bool:
        """Verify that the graph is internally consistent.

        Two levels of checking are performed:

        * An always-on, O(1) structural invariant: a Graph must embed exactly one backing graph -
          either NetworkX or RustworkX, never both or neither. This runs automatically at every
          construction boundary and costs nothing measurable, so it is never gated.

        * An opt-in, O(nodes + edges) thorough audit (see ``_verify_graph_thoroughly``). This is
          expensive enough to matter inside a chain, so it is off by default and controlled by the
          global runtime-checks switch
          (``gerrychain.set_runtime_checks`` / ``gerrychain.runtime_checks``).
          The test suite enables it.

        Args:
            thorough (bool | None): Whether to run the expensive audit. If ``None`` (default),
                follows the global runtime-checks setting. Pass ``True`` to force it on or ``False``
                to force it off (e.g. on hot construction paths that build many short-lived
                subgraphs).

        Returns:
            bool: ``True`` if the graph is valid.

        Raises:
            GraphValidationError: If the graph fails a check.
        """

        nx_set = getattr(self, "_nx_graph", None) is not None
        rx_set = getattr(self, "_rx_graph", None) is not None
        if nx_set == rx_set:  # both set, or neither set
            raise GraphValidationError(
                "Graph is not properly configured: it must embed exactly one backing "
                f"graph (networkx set: {nx_set}, rustworkx set: {rx_set})."
            )

        if thorough is None:
            thorough = runtime_checks_enabled()
        if thorough:
            self._verify_graph_thoroughly()

        return True

    def _verify_graph_thoroughly(self) -> None:
        """Run an expensive O(nodes + edges) structural audit of the backing graph.

        Verifies that every node and edge carries a ``dict`` data payload, which the rest of
        GerryChain relies on. This is the kind of check that is wasteful to run on every chain
        step, so it only runs when runtime checks are enabled (see ``verify_graph_is_valid``).

        Raises:
            GraphValidationError: If a node or edge does not carry a dict payload.
        """
        if self._rx_graph is not None:
            rx_graph = self._rx_graph
            for node_id in rx_graph.node_indices():
                if not isinstance(rx_graph[node_id], dict):
                    raise GraphValidationError(
                        f"Node {node_id} does not carry a dict data payload."
                    )
            for edge_id in rx_graph.edge_indices():
                if not isinstance(rx_graph.get_edge_data_by_index(edge_id), dict):
                    raise GraphValidationError(
                        f"Edge {edge_id} does not carry a dict data payload."
                    )
        elif self._nx_graph is not None:
            nx_graph = self._nx_graph
            for node_id, data in nx_graph.nodes(data=True):
                if not isinstance(data, dict):
                    raise GraphValidationError(
                        f"Node {node_id} does not carry a dict data payload."
                    )
        else:
            raise GraphValidationError("Graph has no NetworkX or RustworkX backing graph.")

    # frm: TODO: Performance:  is_nx_graph() and is_rx_graph() are expensive.
    #
    # Not all of the calls on these routines are needed in production - some are just
    # sanity checking.  Find a way to NOT run this code when in production.

    def is_nx_graph(self) -> bool:
        """Determine if the graph is NX-based."""
        # frm: TODO: Performance:  Only check graph_is_valid() in production
        #
        # Find a clever way to only run this code in development.  Commenting it out for now...
        #     self.verify_graph_is_valid()
        return self._nx_graph is not None

    def get_nx_graph(
        self,
    ) -> networkx.Graph[Hashable, _AttributeDict, _AttributeDict]:
        """Return the embedded NX graph object.

        Returns:
            networkx.Graph:
        """
        if self._nx_graph is None:
            raise TypeError("Graph passed to 'get_nx_graph()' must be a networkx graph")
        return self._nx_graph

    def get_rx_graph(self) -> rustworkx.PyGraph[_AttributeDict, _AttributeDict]:
        """Return the embedded RX graph object.

        Returns:
            rustworkx.PyGraph:
        """
        if self._rx_graph is None:
            raise TypeError("Graph passed to 'get_rx_graph()' must be a rustworkx graph")
        return self._rx_graph

    def is_rx_graph(self) -> bool:
        """Determine if the graph is RX-based."""
        # frm: TODO: Performance:  Only check graph_is_valid() in production
        #
        # Find a clever way to only run this code in development.  Commenting it out for now...
        #     self.verify_graph_is_valid()
        return self._rx_graph is not None

    def convert_from_nx_to_rx(self) -> Graph:
        """Convert an NX-based graph object to be an RX-based graph object.

        The primary use case for this routine is support for users constructing a graph using
        NetworkX functionality and then converting that NetworkX graph to RustworkX when creating a
        Partition object.

        Returns:
            'Graph': An RX-based graph that is "the same" as the given NX-based graph
        """

        # Note that in both cases in the if-stmt below, the nodes are not copied.
        # This is arguably dangerous, but in our case I think it is OK.  Stated
        # differently, the actual node data (the dictionaries) in the original
        # graph (self) will be reused in the returned graph - either because we
        # are just returning the same graph (if it is already based on rx.PyGraph)
        # or if we are converting it from NX.
        #
        self.verify_graph_is_valid()
        if self._nx_graph is not None:
            if self._is_a_subgraph:
                # This routine is intended to be used in exactly one place - in converting
                # an NX based Graph object to be RX based when creating a Partition object.
                # In the future, it might become useful for other reasons, but until then
                # to guard against careless uses, the code will insist that it not be a subgraph.
                raise Exception("convert_from_nx_to_rx(): graph to be converted is a subgraph")

            nx_graph = self._nx_graph
            rx_graph = rustworkx.networkx_converter(nx_graph, keep_attributes=True)
            if not isinstance(rx_graph, rustworkx.PyGraph):
                raise TypeError("NetworkX conversion unexpectedly produced a directed graph")
            rx_graph = cast(rustworkx.PyGraph[_AttributeDict, _AttributeDict], rx_graph)

            # Note that the resulting RX graph will have multigraph set to False which
            # ensures that there is never more than one edge between two specific nodes.
            # This is perhaps not all that interesting in general, but it is critical
            # when getting the edge_id from an edge using RX.edge_indices_from_endpoints()
            # routine - because it ensures that only a single edge_id is returned...

            converted_graph = Graph.from_rustworkx(rx_graph)

            # Some graphs have geometry data (from a geodataframe), so preserve it if it exists
            if hasattr(self, "geometry"):
                setattr(converted_graph, "geometry", getattr(self, "geometry"))

            # Create a mapping from the old NX node_ids to the new RX node_ids (created by
            # RX when it converts from NX)
            nx_to_rx_node_id_map: dict[Hashable, Hashable] = {}
            for node_id in converted_graph.get_rx_graph().node_indices():
                original_node_id = cast(
                    Hashable, converted_graph.node_data(node_id)["__networkx_node__"]
                )
                nx_to_rx_node_id_map[original_node_id] = node_id
            converted_graph.nx_to_rx_node_id_map = nx_to_rx_node_id_map

            # We also have to update the _node_id_to_original_nx_node_id_map to refer to the
            # node_ids in the NX Graph object.
            _node_id_to_original_nx_node_id_map = {}
            for node_id in converted_graph.node_indices:
                original_nx_node_id = converted_graph.node_data(node_id)["__networkx_node__"]
                _node_id_to_original_nx_node_id_map[node_id] = original_nx_node_id
            converted_graph._node_id_to_original_nx_node_id_map = (
                _node_id_to_original_nx_node_id_map
            )

            return converted_graph
        elif self._rx_graph is not None:
            return self
        else:
            raise TypeError(
                "Graph passed to 'convert_from_nx_to_rx()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def get_nx_to_rx_node_id_map(self) -> dict[Hashable, Hashable]:
        """Return the dict that maps NX node_ids to RX node_ids.

        The primary use case for this routine is to support automatically converting NX-based graph
        objects to be RX-based when creating a Partition object. The issue is that when you convert
        from NX to RX the node_ids change and so you need to update the Partition object's
        Assignment to use the new RX node_ids. This routine is used to translate those NX node_ids
        to the new RX node_ids when initializing a Partition object.

        Returns:
            dict[Hashable, Hashable]: NetworkX node IDs mapped to RustworkX node IDs.
        """
        # Simple getter method
        if self._rx_graph is None:
            raise TypeError("Graph passed to 'get_nx_to_rx_node_id()' is not a rustworkx graph")

        if self.nx_to_rx_node_id_map is None:
            raise TypeError("Graph does not have a NetworkX-to-RustworkX node mapping")
        return self.nx_to_rx_node_id_map

    @classmethod
    def from_json(cls, json_file_name: str) -> Graph:
        """Create a :class:`Graph` from a JSON file in NetworkX "adjacency" format.

        This is the standard way to load a dual graph that has already been built and saved to disk;
        it is the inverse of :meth:`to_json`. To build a graph from geospatial data instead (a
        shapefile or a GeoDataFrame), use :meth:`from_file` or :meth:`from_geodataframe`.

        Expected file format:
            The file must contain a single JSON object in the node-link "adjacency" format produced
            by ``networkx.readwrite.json_graph.adjacency_data`` - which is exactly what
            :meth:`to_json` writes, so a file written by ``to_json`` round-trips back through
            ``from_json``. The top-level object has these keys:

            * ``"directed"`` / ``"multigraph"``: booleans. GerryChain graphs are undirected and not
              multigraphs, so both are normally ``false``.
            * ``"graph"``: graph-level attributes as a list of ``[key, value]`` pairs (often empty,
              ``[]``); e.g. a coordinate reference system might live here.
            * ``"nodes"``: a list of node objects. Each has an ``"id"`` plus any number of arbitrary
              attributes (population, district, county, geometry, ...).
            * ``"adjacency"``: a list parallel to ``"nodes"``. ``adjacency[i]`` is the list of edges
              incident to node ``i``; each edge object has the neighbor's ``"id"`` plus any edge
              attributes (e.g. ``"shared_perim"``).

            A minimal two-node example::

                {
                  'directed': false, "multigraph": false, "graph": [],
                  'nodes': [{"pop": 5, "id": 0}, {"pop": 3, "id": 1}],
                  'adjacency': [[{"id": 1}], [{"id": 0}]]
                }

            Node and edge attributes are preserved and become accessible as
            ``graph.node_data(node_id)[attr]`` and ``graph.edge_data(edge_id)[attr]``. Anything you
            intend to use later (a population column for ``pop_col``, a ``region_surcharge``
            attribute, an election column, ...) must already be present as a node attribute here.

        Backend:
            The returned ``Graph`` is **NetworkX-backed**, which is convenient for inspection and
            editing. When you later wrap it in a :class:`~gerrychain.Partition`, GerryChain converts
            it to the faster RustworkX backend automatically. Node ids are taken verbatim from the
            ``"id"`` fields; note that the RustworkX conversion reassigns node ids to a contiguous
            integer range, so do not rely on a node's id carrying semantic meaning.

        Side effect (data warnings):
            After loading, this calls :meth:`issue_warnings`, which warns about "islands" - degree-0
            nodes. An island usually indicates a problem with the dual graph (a unit with no recorded
            adjacencies) and will break contiguity-based proposals, so the warning is worth heeding.

        Args:
            json_file_name (str): Path to the JSON file to read. This is an ordinary filesystem
                path; the file is opened and parsed directly.

        Returns:
            Graph: A NetworkX-backed GerryChain ``Graph`` containing the nodes, edges, and attributes
            described by the file.

        Raises:
            FileNotFoundError: If ``json_file_name`` does not exist.
            json.JSONDecodeError: If the file does not contain valid JSON.
            KeyError: If the JSON is valid but is not in the expected adjacency format.

        Example:
            >>> from gerrychain import Graph
            >>> graph = Graph.from_json("./my_state.json")  # doctest: +SKIP

            If you just want a graph to experiment with, GerryChain bundles a ready-made example,
            which needs no file at all::

                from gerrychain.examples import gerrymandria
                graph = gerrymandria()
        """

        # Note that this returns an NX-based Graph object.  At some point in
        # the future, if we embrace an all RX world, it will make sense to
        # have it produce an RX-based Graph object.

        with open(json_file_name) as f:
            data = json.load(f)

        # A bit of Python magic - an adjacency graph is a dict of dict of dicts
        # which is structurally equivalent to a NetworkX graph, so you can just
        # pretend that is what it is and it all works.
        nx_graph = json_graph.adjacency_graph(data)

        graph = cls.from_networkx(nx_graph)
        graph.issue_warnings()
        return graph

    def to_json(self, json_file_name: str, include_geometries_as_geojson: bool = False) -> None:
        """Write this :class:`Graph` to disk as a JSON file in NetworkX "adjacency" format.

        This is the inverse of :meth:`from_json`: it serializes the graph - every node and edge,
        with all of their attributes - to the node-link "adjacency" format produced by
        ``networkx.readwrite.json_graph.adjacency_data``, so a file written here can be read back
        with :meth:`from_json`. See :meth:`from_json` for a description of the on-disk structure.

        Backend requirement (NetworkX only):
            ``to_json`` currently only works on a **NetworkX-backed** graph and raises ``TypeError``
            otherwise. This matters in practice because wrapping a graph in a
            :class:`~gerrychain.Partition` converts it to the RustworkX backend, so the graph
            reached via ``partition.graph`` cannot be serialized directly - keep a reference to the
            original NetworkX ``Graph`` (e.g. the one returned by
            :meth:`from_json` / :meth:`from_file`) if you need to write it out. (Serializing an
            RX-backed graph is a planned enhancement.)

        Geometries:
            Graphs built from geospatial data (:meth:`from_file` / :meth:`from_geodataframe`) carry
            a ``shapely`` geometry object on each node, which is not JSON-serializable. The
            ``include_geometries_as_geojson`` flag decides what happens to those geometry attributes
            (it has no effect on graphs that have no geometry):

            * ``False`` (default): geometry attributes are **dropped** from the output. The file is
              smaller, but the geometry is not saved, so a round-trip through :meth:`from_json` will
              not recover it.
            * ``True``: each geometry is **converted to GeoJSON** (its ``__geo_interface__``) and
              written into the file, preserving it. Note that reading the file back returns those
              attributes as GeoJSON dicts, not as ``shapely`` objects.

        Non-JSON-native values:
            Attribute values that the standard JSON encoder cannot handle are passed through
            :func:`json_serialize`, which converts pandas / numpy integer values to plain Python
            ``int`` (a common result of building a graph from a GeoDataFrame).

        Args:
            json_file_name (str): Path of the JSON file to write. An existing file is overwritten.
            include_geometries_as_geojson (bool, optional): Whether to write node geometries to the
                file as GeoJSON (``True``) or strip them out (``False``, the default). See
                "Geometries" above.

        Returns:
            None: The graph is written to ``json_file_name``.

        Raises:
            TypeError: If this graph is not NetworkX-backed (e.g. an RX-backed graph, such as the
                one inside a Partition).
            OSError: If the file cannot be opened or written.

        Example:
            >>> from gerrychain import Graph
            >>> graph = Graph.from_json("./my_state.json")  # doctest: +SKIP
            >>> graph.to_json("./my_state_copy.json")       # doctest: +SKIP
        """
        # frm TODO: Code: Implement graph.to_json for an RX based graph
        if self._nx_graph is None:
            raise TypeError("Graph passed to 'to_json()' is not a networkx graph")

        data = cast(_AdjacencyData, json_graph.adjacency_data(self.get_nx_graph()))

        if include_geometries_as_geojson:
            convert_geometries_to_geojson(data)
        else:
            remove_geometries(data)

        with open(json_file_name, "w") as f:
            json.dump(data, f, default=json_serialize)

    @classmethod
    def from_file(
        cls,
        filename: str,
        adjacency: str = "rook",
        cols_to_add: list[str] | None = None,
        reproject: bool = False,
        ignore_errors: bool = False,
    ) -> Graph:
        """Create a Graph from a shapefile, GeoPackage, GeoJSON, or similar source.

        This method reads any format that `geopandas` can load and builds a graph from it.

        See `from_geodataframe` for more details.

        Args:
            filename (str): Path to the shapefile / GeoPackage / GeoJSON / etc.
            adjacency (str, optional): The adjacency type to use ("rook" or "queen"). Default is
                "rook"
            cols_to_add (list[str] | None, optional): The names of the columns that you want to
                add to the graph as node attributes. Default is None.
            reproject (bool, optional): Whether to reproject to a UTM projection before creating
                the graph. Default is False.
            ignore_errors (bool, optional): Whether to ignore all invalid geometries and try to
                continue creating the graph. Default is False.

        Returns:
            Graph: The Graph object of the geometries from `filename`.

        Warning:
            This method requires the optional ``geopandas`` dependency.
            Install ``gerrychain`` with the ``geo`` extra via
            ``pip install gerrychain[geo]``, or install ``geopandas`` separately.
        """

        df = gp.read_file(filename)
        graph = cls.from_geodataframe(
            df,
            adjacency=adjacency,
            cols_to_add=cols_to_add,
            reproject=reproject,
            ignore_errors=ignore_errors,
        )

        # Store CRS data as an attribute of the NX graph
        graph.get_nx_graph().graph["crs"] = df.crs.to_json() if df.crs is not None else None
        return graph

    @classmethod
    def from_geodataframe(
        cls,
        dataframe: gp.GeoDataFrame,
        adjacency: str = "rook",
        cols_to_add: list[str] | None = None,
        reproject: bool = False,
        ignore_errors: bool = False,
        crs_override: str | int | None = None,
    ) -> Graph:
        """Create the adjacency Graph of geometries described by `dataframe`.

        The areas of the polygons are included as node attributes (with key `area`). The shared
        perimeter of neighboring polygons are included as edge attributes (with key
        `shared_perim`).

        Nodes corresponding to polygons on the boundary of the union of all the geometries (e.g.,
        the state, if your dataframe describes VTDs) have a `boundary_node` attribute (set to
        `True`) and a `boundary_perim` attribute with the length of this "exterior" boundary.

        By default, areas and lengths are computed in a UTM projection suitable for the geometries.
        This prevents the bizarro area and perimeter values that show up when you accidentally do
        computations in Longitude-Latitude coordinates. If the user specifies `reproject=False`,
        then the areas and lengths will be computed in the GeoDataFrame's current coordinate
        reference system. This option is for users who have a preferred CRS they would like to use.

        Args:
            dataframe (GeoDataFrame): The GeoDateFrame to convert
            adjacency (str, optional): The adjacency type to use ("rook" or "queen"). Default is
                "rook".
            cols_to_add (list[str] | None, optional): The names of the columns that you want to
                add to the graph as node attributes. Default is None.
            reproject (bool, optional): Whether to reproject to a UTM projection before creating
                the graph. Default is ``False``.
            ignore_errors (bool, optional): Whether to ignore all invalid geometries and attept to
                create the graph anyway. Default is ``False``.
            crs_override (str | int | None, optional): Value to override the CRS of the
                GeoDataFrame. Default is None.

        Returns:
            Graph: The adjacency graph of the geometries from `dataframe`. Note that the returned
                Graph object has an embedded NetworkX graph (not a RustworkX graph).
        """
        # Validate geometries before reprojection
        if not ignore_errors:
            invalid = invalid_geometries(dataframe)
            if len(invalid) > 0:
                raise GeometryError(
                    f"Invalid geometries at rows {invalid} before "
                    "reprojection. Consider repairing the affected geometries with "
                    "`.buffer(0)`, or pass `ignore_errors=True` to attempt to create "
                    "the graph anyways."
                )

        # Project the dataframe to an appropriate UTM projection unless
        # explicitly told not to.
        if reproject:
            df = reprojected(dataframe)
            if ignore_errors:
                invalid_reproj = invalid_geometries(df)
                print(invalid_reproj)
                if len(invalid_reproj) > 0:
                    raise GeometryError(
                        f"Invalid geometries at rows {invalid_reproj} after "
                        "reprojection. Consider reloading the GeoDataFrame with "
                        "`reproject=False` or repairing the affected geometries "
                        "with `.buffer(0)`."
                    )
        else:
            df = dataframe

        # Generate dict of dicts of dicts with shared perimeters according
        # to the requested adjacency rule
        adjacencies = neighbors(df, adjacency)  # Note - this is adjacency.neighbors()

        nx_graph = cast(
            "networkx.Graph[Hashable, _AttributeDict, _AttributeDict]",
            networkx.Graph(adjacencies),
        )

        # The geometry attribute on df is a special attribute that only appears on
        # geodataframes. This is just a list of polygons representing some real-life
        # geometries underneath a certain projection system (CRS). These polygons can
        # then be fed to matplotilb to make nice plots of things, or they can be used
        # to compute things like area and perimeter for use in updaters and validators
        # that employ some sort of Reock score (uncommon, but unfortunately necessary in
        # some jurisdictions).
        #

        # TODO: Think about whether to change the way we store geometry information
        #
        # We probably don't need to store this as an attribute on
        # the Graph._nxgraph object (or the Graph._rxgraph) object, however. In fact, it
        # might be best to just make a Graph.dataframe attribute to store all of the
        # graph data on, and add attributes to _nxgraph and _rxgraph nodes as needed

        setattr(nx_graph, "geometry", df.geometry)

        # Add "exterior" perimeters to the boundary nodes
        _add_boundary_perimeters_to_nx_graph(nx_graph, df.geometry)

        # Add area data to the nodes
        areas = df.geometry.area.to_dict()
        networkx.set_node_attributes(nx_graph, name="area", values=areas)

        if crs_override is not None:
            df.set_crs(crs_override, inplace=True)

        if df.crs is None:
            warnings.warn(
                "GeoDataFrame has no CRS. Did you forget to set it? "
                "If you're sure this is correct, you can ignore this warning. "
                "Otherwise, please set the CRS using the `crs_override` parameter. "
                "Attempting to proceed without a CRS."
            )
            nx_graph.graph["crs"] = None
        else:
            nx_graph.graph["crs"] = df.crs.to_json()

        graph = cls.from_networkx(nx_graph)

        # frm: Moved from earlier in the function so that we would have a Graph
        #       object (vs. NetworkX.Graph object)

        graph.add_data(df, columns=cols_to_add)
        graph.issue_warnings()

        return graph

    # Performance Note:
    #
    # Most of the functions in the Graph class will be called after a
    # partition has been created and the underlying graph converted
    # to be based on RX.  So, by testing first for RX we actually
    # save a significant amount of time because we do not need to
    # also test for NX (if you test for NX first then you do two tests).
    #

    @property
    def node_indices(self) -> set[Hashable]:
        """Return a ``set`` of the node_ids in the graph.

        This is the canonical accessor for the graph's node_ids. It returns a ``set``, so it is
        suited to membership tests (``node in graph.node_indices``) and de-duplication, but it is
        unordered. If you need an ordered, indexable sequence of the same node_ids, use
        :attr:`nodes` (which returns a ``list``). Prefer ``node_indices`` unless list semantics are
        specifically required.

        Returns:
            set[Hashable]: An unordered set of node IDs in the graph.
        """
        if self._rx_graph is not None:
            return set(self._rx_graph.node_indices())
        elif self._nx_graph is not None:
            return set(self._nx_graph.nodes)
        else:
            raise TypeError(
                "Graph passed to 'node_indices()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    @property
    def edge_indices(self) -> set[Hashable]:
        """Return a ``set`` of the edge *ids* in the graph.

        Unlike :attr:`nodes`/:attr:`node_indices` (which carry the same content up to a
        permutation), ``edge_indices`` and :attr:`edges` are genuinely different: ``edge_indices``
        returns edge *ids* (opaque integers under RustworkX), while :attr:`edges` returns the edges
        themselves as ``(u, v)`` tuples of node_ids. Use an edge id with
        :meth:`get_edge_from_edge_id` / :meth:`get_edge_id_from_edge` to convert between the two.

        Returns:
            set[Hashable]: The edge IDs in the graph.
        """
        if self._rx_graph is not None:
            # A set of edge_ids for the edges
            return set(self._rx_graph.edge_indices())
        elif self._nx_graph is not None:
            # A set of edge_ids (tuples) extracted from the graph's EdgeView
            return set(self._nx_graph.edges)
        else:
            raise TypeError(
                "Graph passed to 'edge_indices()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def get_edge_from_edge_id(self, edge_id: Hashable) -> tuple[Hashable, Hashable]:
        """Return the edge (tuple of node_ids) corresponding to the given edge_id.

        Note that in NX, an edge_id is the same as an edge - it is just a tuple of node_ids.
        However, in RX, an edge_id is an integer, so if you want to get the tuple of node_ids you
        need to use the edge_id to get that tuple...

        Args:
            edge_id (Hashable): The desired edge ID.

        Returns:
            tuple[Hashable, Hashable]: The edge's node IDs.
        """

        if self._rx_graph is not None:
            # In RX, we need to go get the edge tuple
            endpoints = self._rx_graph.get_edge_endpoints_by_index(cast(int, edge_id))
            return (endpoints[0], endpoints[1])
        elif self._nx_graph is not None:
            # In NX, the edge_id is also the edge tuple
            return cast(tuple[Hashable, Hashable], edge_id)
        else:
            raise TypeError(
                "Graph passed to 'get_edge_from_edge_id()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def get_edge_id_from_edge(self, edge: tuple[Hashable, Hashable]) -> Hashable:
        """Get the edge_id that corresponds to the given edge.

        In RX an edge_id is an integer that designates an edge (an edge is a tuple of node_ids). In
        NX, an edge_id IS the tuple of node_ids. So, in general, to support both NX and RX, if you
        want to get access to the edge data for an edge (tuple of node_ids), you need to ask for
        the edge_id.

        Args:
            edge (tuple[Hashable, Hashable]): A tuple of node IDs.

        Returns:
            Hashable: The ID associated with the edge.
        """

        if self._rx_graph is not None:
            # frm: TODO: Performance: Perhaps get_edge_id_from_edge() is too expensive...
            #
            # If this routine becomes a signficant performance issue, then perhaps
            # we can change the algorithms that use it so that it is not needed.
            # In particular, there are several routines in tree.py that use it
            # by traversing chains of nodes (successors and predecessors) which
            # requires the code to recreate the edges from the nodes in hand.  This
            # was not a problem in an NX world - the tuple of nodes was exactly what
            # and edge_id was, but in the RX world it is not - necessitating this routine.
            #
            # BUT...  If the code had chains of edges rather than chains of nodes,
            # then you could have the edge_ids at hand already and avoid having to
            # do this lookup.
            #
            # However, it may be that the RX edge_indices_from_endpoints() is smart
            # enough (for instance if it caches a dict mapping) that the performance
            # hit is minimal...  Here's to hoping that RX is "smart enough"... ;-)

            # Note that while in general the routine, edge_indices_from_endpoints(),
            # can return more than one edge in the case of a Multi-Graph (a graph that
            # allows more than one edge between two nodes), we can rely on it only
            # returning a single edge because the RX graph object has multigraph set
            # to false by RX.networkx_converter() - because the NX graph was undirected...
            #
            edge_indices = self._rx_graph.edge_indices_from_endpoints(
                cast(int, edge[0]), cast(int, edge[1])
            )
            return edge_indices[0]  # there will always be one and only one
        elif self._nx_graph is not None:
            # In NX, the edge_id is also the edge tuple
            return edge
        else:
            raise TypeError(
                "Graph passed to 'get_edge_id_from_edge()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    @property
    def nodes(self) -> list[Hashable]:
        """Return a ``list`` of all of the node_ids in the graph.

        This returns the same node_ids as :attr:`node_indices`, the difference being only the
        container type: ``nodes`` returns an ordered, indexable ``list`` maintaining the backend's
        node insertion order while ``node_indices`` returns an unordered ``set``. Prefer
        :attr:`node_indices` unless you specifically need list semantics (ordering or indexing).

        Note the related distinction for edges: :attr:`edges` returns the edges themselves (tuples
        of node_ids), whereas :attr:`edge_indices` returns edge *ids* (integers under RustworkX).
        That object-vs-id distinction is load-bearing for edges, but for nodes the node and its id
        coincide, which is why ``nodes`` and ``node_indices`` carry the same content.

        There is also a minor subtlety that users are unlikely to encounter unless accessing the
        graph attribute off of a Partition object, but it is worth noting: the node_ids in the
        graph attribute of a Partition object are not necessarily the same as the node_ids in the
        original graph that was used to create the Partition object. Before the move to RustworkX
        it was common to create nodes whose ids were either meaningful (e.g., the FIPS code of a
        VTD), a subset of node ids of another graph (when the graph was a subgraph), or some
        coordinate pairs (common with grid graphs). That is not true of RustworkX node_ids, so
        any code that relies on the semantics of a node's id (treating it like a name) is suspect
        in the RustworkX world.

        Returns:
            list[Hashable]: An ordered list of node IDs in the graph.
        """

        # Note: graph.nodes continues to exist because it was used often in legacy code.
        #
        if self._rx_graph is not None:
            # A list of integer node_ids
            return _NodeCollection(self._rx_graph.node_indices())
        elif self._nx_graph is not None:
            # For subgraphs, serve the canonical order captured in subgraph(): iterating the
            # NX view directly is hash-ordered when the view is under half its parent's size.
            if self._nx_node_order is not None:
                return _NodeCollection(self._nx_node_order)
            # A list of node_ids -
            return _NodeCollection(self._nx_graph.nodes)
        else:
            raise TypeError(
                "Graph passed to 'nodes()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    @property
    def edges(self) -> set[tuple[Hashable, Hashable]]:
        """Return a ``set`` of all of the edges in the graph, where each edge is a ``(u, v)`` tuple
        of node_ids.

        This returns the edges themselves, which may not be the same as their ids (in fact, for
        RustworkX backed graphs, they are guaranteed to be different). For the edge *ids* (opaque
        integers under RustworkX) see :attr:`edge_indices`.

        Returns:
            set[tuple[Hashable, Hashable]]: One ``(u, v)`` node ID tuple per edge.
        """
        # Return a set of edge tuples

        if self._rx_graph is not None:
            # A set of tuples for the edges
            return _EdgeCollection(self._rx_graph.edge_list())
        elif self._nx_graph is not None:
            # A set of tuples extracted from the graph's EdgeView
            return _EdgeCollection(self._nx_graph.edges)
        else:
            raise TypeError(
                "Graph passed to 'edges()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def add_edge(self, node_id1: Hashable, node_id2: Hashable) -> None:
        """Add an edge to the graph from node_id1 to node_id2.

        Note that both nodes need to already be members of the graph

        Args:
            node_id1 (Hashable): One node ID in the edge.
            node_id2 (Hashable): The other node ID in the edge.

        """

        # Note: the add_edge() routine is not used in the GerryChain codebase.
        #
        # It remains for legacy reasons, and because users may find it convenient
        # to operate on a gerrychain Graph instead of an NX graph.

        if self._rx_graph is not None:
            rx_node_id1, rx_node_id2 = cast(int, node_id1), cast(int, node_id2)
            node1_exists = self._rx_graph.has_node(rx_node_id1)
            node2_exists = self._rx_graph.has_node(rx_node_id2)
            if (not node1_exists) or (not node2_exists):
                raise Exception("add_edge(): both nodes in the edge must already exist")
            # empty dict tells RX the edge data will be a dict
            self._rx_graph.add_edge(rx_node_id1, rx_node_id2, {})
        elif self._nx_graph is not None:
            node1_exists = self._nx_graph.has_node(node_id1)
            node2_exists = self._nx_graph.has_node(node_id2)
            if (not node1_exists) or (not node2_exists):
                raise Exception("add_edge(): both nodes in the edge must already exist")
            self._nx_graph.add_edge(node_id1, node_id2)
        else:
            raise TypeError(
                "Graph passed to 'add_edge()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def add_data(self, df: pd.DataFrame, columns: Iterable[str] | None = None) -> None:
        """Add columns of a DataFrame to a graph as node attributes by matching the DataFrame's.

        Args:
            df (DataFrame): Dataframe containing given columns.
            columns (Iterable[str] | None, optional): list of dataframe column names to add.
                Default is None.

        """

        if not (self._nx_graph is not None):
            raise TypeError("Graph passed to 'add_data()' is not a networkx graph")

        columns = list(df.columns if columns is None else columns)

        selected = cast(pd.DataFrame, df[columns])
        check_dataframe(selected)

        # Create dict: {node_id: {attr_name: attr_value}}
        column_dictionaries = df.to_dict("index")
        nx_graph = self._nx_graph
        networkx.set_node_attributes(nx_graph, column_dictionaries)

        data = getattr(nx_graph, "data", None)
        if data is not None:
            data[columns] = df[columns]
        else:
            setattr(nx_graph, "data", df[columns])

    def join(
        self,
        dataframe: pd.DataFrame,
        columns: list[str] | None = None,
        left_index: str | None = None,
        right_index: str | None = None,
    ) -> None:
        """Add data from a dataframe to the graph, matching nodes to rows when the node's.

        Add data from a dataframe to the graph, matching nodes to rows when the node's `left_index`
        attribute equals the row's `right_index` value.

        Args:
            dataframe (DataFrame): DataFrame.
            columns (list[str] | None, optional): The columns whose data you wish to add to the
                graph. If not provided, all columns are added. Default is None.
            left_index (str | None, optional): The node attribute used to match nodes to rows.
                If not provided, node IDs are used. Default is None.
            right_index (str | None, optional): The DataFrame column name to use to match rows
                to nodes. If not provided, the DataFrame's index is used. Default is None.

        """
        if right_index is not None:
            df = dataframe.set_index(right_index)
        else:
            df = dataframe

        if columns is not None:
            df = cast(pd.DataFrame, df[columns])

        check_dataframe(df)

        column_dictionaries = df.to_dict()

        # In the future it might make sense to support this for RX...
        if self._nx_graph is None:
            raise TypeError("Graph passed to join() is not a networkx graph")
        nx_graph = self._nx_graph

        if left_index is not None:
            ids_to_index = networkx.get_node_attributes(nx_graph, left_index)
        else:
            # When the left_index is node ID, the matching is just
            # a redundant {node: node} dictionary
            ids_to_index = dict(zip(self.nodes, self.nodes))

        node_attributes = {
            node_id: {column: values[index] for column, values in column_dictionaries.items()}
            for node_id, index in ids_to_index.items()
        }

        networkx.set_node_attributes(nx_graph, node_attributes)

    @property
    def islands(self) -> set[Hashable]:
        """Return A set of all node_ids for nodes of degree 0.

        Return a set of all node_ids that are not connected via an edge to any other node in the
        graph - that is, nodes with degree = 0

        Returns:
            set[Hashable]: Node IDs for nodes of degree zero.
        """
        # Return all nodes of degree 0 (those not connected in an edge to another node)
        return set(node_id for node_id in self.node_indices if self.degree(node_id) == 0)

    def is_directed(self) -> bool:
        """Returns False, because GerryChain graphs are not directed.

        This is used by low level routines that can operate on both directed and un-directed
        graphs, that is, it exists so that we can use off-the-shelf code that needs to know if the
        graph is directed or not.

        Returns:
            bool: False
        """

        return False

    def warn_for_islands(self) -> None:
        """Issue a warning if there are any islands in the graph.

        Raises:
            Warning: If there are any islands in the graph, a warning is issued with the indices of
                the islands.
        """
        islands = self.islands
        if len(self.islands) > 0:
            warnings.warn(f"Found islands (degree-0 nodes). Indices of islands: {islands}")

    def issue_warnings(self) -> None:
        """Issue any warnings concerning the content or structure of the graph."""
        self.warn_for_islands()

    def __len__(self) -> int:
        """Return the number of nodes in the graph.

        Returns:
            int:
        """
        return len(self.node_indices)

    def __getattr__(self, __name: str) -> Any:
        """Delegate unknown attributes to the embedded NetworkX backing graph.

        Accesses that Graph itself does not define are forwarded to the embedded NetworkX graph.
        This keeps backend conveniences reachable - e.g. ``graph.geometry`` (stored on the NX
        graph) or ``graph.graph["crs"]`` (the NX graph-level attribute dict) - and lets an
        NX-backed Graph be passed to NetworkX algorithms.

        Delegation is intentionally NX-only. Forwarding to a RustworkX backing graph would leak
        rustworkx's raw integer-index API, the very distinction this wrapper exists to hide, and
        none of those conveniences exist on a PyGraph anyway; an RX-backed Graph raises
        AttributeError here instead.

        Two safety rules apply:

        * Dunder / introspection names are never delegated. Forwarding names like
          ``__deepcopy__`` / ``__getstate__`` / ``__test__`` to the backing graph would leak
          copy/pickle/introspection probes into it; we raise AttributeError so the normal Python
          machinery handles them.
        * Because ``_nx_graph`` has a class-level None default, reading it here can never fall
          back into ``__getattr__`` - so the infinite-recursion hazard that used to require a
          special-case guard is gone by construction.

        Args:
            __name (str): The attribute being requested.

        Returns:
            Any: The dynamically delegated attribute value from the NetworkX graph.

        Raises:
            AttributeError: If the name is a dunder, the Graph is not NetworkX-backed, or the NX
                graph has no such attribute.
        """
        if __name.startswith("__") and __name.endswith("__"):
            raise AttributeError(__name)

        if self._nx_graph is not None:
            return getattr(self._nx_graph, __name)

        raise AttributeError(
            f"'Graph' object has no attribute {__name!r}. Attribute delegation is only "
            "supported for NetworkX-backed graphs (e.g. to reach '.geometry' or graph-level "
            "attributes); it is not forwarded to a RustworkX backing graph."
        )

    def __getitem__(self, node_id: Hashable) -> Mapping[Hashable, _AttributeDict]:
        if self._rx_graph is not None:
            # frm TODO: Code: Decide if __getitem__() should work for RX
            raise TypeError("Graph._getitem__() is not defined for a rustworkx graph")
        elif self._nx_graph is not None:
            return self._nx_graph[node_id]
        else:
            raise TypeError(
                "Graph passed to '__getitem__()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def __iter__(self) -> Iterator[Hashable]:
        """Yields the node_ids in the graph.

        Returns:
            Iterator[Hashable]: The graph's node IDs.
        """
        yield from self.node_indices

    def subgraph(self, nodes: Iterable[Hashable]) -> Graph:
        """Create a subgraph that contains the given nodes.

        Note that creating a subgraph of an RustworkX (RX) graph renumbers the nodes, so that a
        node that had node_id: 4 in the parent graph might have node_id: 2 in the subgraph. This is
        a HUGE difference from the NX world where the node_ids in a subgraph do not change from
        those in the parent graph.

        In order to make sense of the nodes in a subgraph in the RX world, we need to maintain
        mappings from the node_ids in the subgraph to the node_ids of the immediate parent graph
        and to the "original" top-level graph that contains all of the nodes. You will notice the
        creation of those maps in the code below.

        Args:
            nodes (Iterable[Hashable]): Nodes to include in the subgraph.

        Returns:
            'Graph': A subgraph containing the given nodes.
        """

        """
        Subgraphs in RustworkX:

        Subgraphs are one of the biggest differences between NX and RX, because RX creates new
        node_ids for the nodes in the subgraph, integer node_ids starting at 0 with no gaps.
        So, if you create a subgraph with a list of nodes: [45, 46, 47] the nodes in the
        subgraph will be [0, 1, 2].

        This creates problems for functions that operate on subgraphs and want to return results
        involving node_ids to the caller.  To solve this, we define a
        _node_id_to_parent_node_id_map whenever we create a subgraph that will provide the node_id
        in the parent for each node in the subgraph. For NX this is a no-op, and the
        _node_id_to_parent_node_id_map is just an identity map - each node_id is
        mapped to itself.  For RX, however, we store the parent_node_id in the node's data before
        creating the subgraph, and then in the subgraph, we use the parent's node_id to construct
        a map from the subgraph node_id to the parent_node_id.

        This means that any function that wants to return results involving node_ids can safely
        translate node_ids using the _node_id_to_parent_node_id_map, so that the results make
        sense in the caller's context.

        A note of caution: if the caller retains the subgraph after using it in a function call,
        the caller should almost certainly not use the node_ids in the subgraph for ANYTHING.
        It would be safest to reset the value of the subgraph to None after using it.  To
        prevent subgraph node_ids from leaking into code where they would be dangerous, all
        calls to subgraph() in the GerryChain codebase are made as actual parameters to a
        function call so that the node_ids of the subgraph cannot leak into the calling routine's
        code.

        Also, for both RX and NX, we set the _node_id_to_parent_node_id_map to be the identity map
        for top-level graphs on the off chance that there is a function that takes both top-level
        graphs and subgraphs as a parameter.  This allows the function to always do the node
        translation. In the case of a top-level graph the translation will be a no-op, but it will
        be correct.

        Also, we set the _is_a_subgraph = True, so that we can detect whether a parameter passed
        into a function is a top-level graph or not.  This will allow us to debug the code to
        determine if assumptions about a parameter always being a subgraph is accurate.  It also
        helps to educate future readers of the code that subgraphs are "interesting"...
        """

        nodes = list(nodes)
        new_subgraph = None

        if self._nx_graph is not None:
            # Canonicalize to the parent's node order. Callers often pass a set, and the
            # node order of a subgraph *view* of an NX graph is not guaranteed to be the same
            # as the parent graph. See the bottom of
            # https://networkx.org/documentation/stable/reference/classes/generated/networkx.Graph.subgraph.html
            # for an example.
            #
            # In fact, the NX subgraph view enumerates its nodes in set (hash-dependent) order
            # whenever the view is smaller than half its parent (networkx show_nodes/FilterAtlas).
            # FilterAtlas.__iter__ is the atlas that backs a subgraph view's node dict and
            # adjacency rows.
            #
            # Link for reference:
            # https://github.com/networkx/networkx/blob/7530809bfa1ea7ed6fdf918a4d1431488953cb1f/networkx/classes/coreviews.py#L293
            #
            # Extracted code snippet:
            #
            # """
            # def __iter__(self):
            #     try:  # check that NODE_OK has attr 'nodes'
            #         node_ok_shorter = 2 * len(self.NODE_OK.nodes) < len(self._atlas)
            #     except AttributeError:
            #         node_ok_shorter = False
            #     if node_ok_shorter:
            #         return (n for n in self.NODE_OK.nodes if n in self._atlas)
            #     return (n for n in self._atlas if self.NODE_OK(n))
            # """

            node_set = set(nodes)
            ordered_nodes = [node for node in self.nodes if node in node_set]
            nx_subgraph = self._nx_graph.subgraph(ordered_nodes)

            new_subgraph = self.from_networkx(nx_subgraph)
            new_subgraph._nx_node_order = ordered_nodes
            # for NX, the node_ids in subgraph are the same as in the parent graph
            _node_id_to_parent_node_id_map = {node: node for node in ordered_nodes}
            _node_id_to_original_nx_node_id_map = {node: node for node in ordered_nodes}
        elif self._rx_graph is not None:
            # For RX, the node_ids in the subgraph change, so we need a way to map subgraph node_ids
            # into parent graph node_ids.  To do so, we add the parent node_id into the node data
            # so that in the subgraph we can find it and then create the map.
            #
            # Note that this works because the node_data dict is shared by the nodes in both the
            # parent graph and the subgraph, so we can set the "parent" node_id in the parent before
            # creating the subgraph, and that value will be available in the subgraph even though
            # the subgraph will have a different node_id for the same node.
            #
            # This value is removed from the node_data below after creating the subgraph.
            #
            for node_id in nodes:
                self.node_data(node_id)["parent_node_id"] = node_id

            # It is also important for all RX graphs (subgraphs or top-level graphs) to have
            # a mapping from RX node_id to the "original" NX node_id.  However, we do not need
            # to do what we do with the _node_id_to_parent_node_id_map and set the value of
            # the "original" node_id now, because this value never changes for a node.  It
            # should already have been set for each node by the standard RX code that
            # converts from NX to RX (which sets the "__networkx_node__" attribute to be
            # the NX node_id).  We just check to make sure that it is in fact set.
            #
            for node_id in nodes:
                if "__networkx_node__" not in self.node_data(node_id):
                    raise Exception("subgraph: internal error: original_nx_node_id not set")

            rx_subgraph = self._rx_graph.subgraph(cast(list[int], nodes))
            new_subgraph = self.from_rustworkx(rx_subgraph)

            # frm: Create the map from subgraph node_id to parent graph node_id
            _node_id_to_parent_node_id_map = {}
            for subgraph_node_id in new_subgraph.node_indices:
                _node_id_to_parent_node_id_map[subgraph_node_id] = new_subgraph.node_data(
                    subgraph_node_id
                )["parent_node_id"]
                # value no longer needed, so delete it
                new_subgraph.node_data(subgraph_node_id).pop("parent_node_id")

            # frm: Create the map from subgraph node_id to the original graph's node_id
            _node_id_to_original_nx_node_id_map = {}
            for subgraph_node_id in new_subgraph.node_indices:
                _node_id_to_original_nx_node_id_map[subgraph_node_id] = new_subgraph.node_data(
                    subgraph_node_id
                )["__networkx_node__"]
        else:
            raise TypeError(
                "Graph passed to 'subgraph()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

        new_subgraph._is_a_subgraph = True
        new_subgraph._node_id_to_parent_node_id_map = _node_id_to_parent_node_id_map
        new_subgraph._node_id_to_original_nx_node_id_map = _node_id_to_original_nx_node_id_map

        return new_subgraph

    def translate_subgraph_node_ids_for_flips(
        self, flips: dict[Hashable, Hashable]
    ) -> dict[Hashable, Hashable]:
        """Translate the given flips so that the subgraph node_ids in the flips correspond
        to the appropriate node_ids in the parent graph.

        The flips parameter is a dict mapping node_ids to parts (districts).

        This routine is used when a computation that creates flips is made on a subgraph, but those
        flips want to be translated into the context of the parent graph at the end of the
        computation.

        For more details, refer to the larger comment on subgraphs...

        Args:
            flips (dict[Hashable, Hashable]): A dictionary associating nodes with new
                part in a partition (a "part" is the same as a district in common parlance).

        Returns:
            dict[Hashable, Hashable]: Flips translated to use node IDs
                appropriate for the parent graph
        """

        translated_flips = {}
        for subgraph_node_id, part in flips.items():
            parent_node_id = self._node_id_to_parent_node_id_map[subgraph_node_id]
            translated_flips[parent_node_id] = part

        return translated_flips

    def translate_subgraph_node_ids_for_set_of_nodes(
        self, set_of_nodes: AbstractSet[Hashable]
    ) -> set[Hashable]:
        """Translate the given set_of_nodes to have the appropriate node_ids for the parent graph.

        This routine is used when a computation that creates a set of nodes is made on a subgraph,
        but those nodes want to be translated into the context of the parent graph at the end of
        the computation.

        For more details, refer to the larger comment on subgraphs...

        Args:
            set_of_nodes (AbstractSet[Hashable]): Node IDs in a subgraph.

        Returns:
            set[Hashable]: Node IDs translated to have the IDs appropriate
                for the parent graph
        """
        # This routine replaces the node_ids of the subgraph with the node_ids
        # for the same node in the parent graph.  This routine is used to
        # when a computation is made on a subgraph but the resulting set of nodes
        # being returned want to be the appropriate node_ids for the parent graph.
        translated_set_of_nodes = set()
        for node_id in set_of_nodes:
            translated_set_of_nodes.add(self._node_id_to_parent_node_id_map[node_id])
        return translated_set_of_nodes

    def _generic_bfs_edges(
        self, source: Hashable
    ) -> Generator[tuple[Hashable, Hashable], None, None]:
        """Yield parent/child pairs in a breadth first traversal of the graph starting at "source".

        Args:
            source (Hashable): The first parent node ID, which starts the
                breadth first search

        Returns:
            Generator[tuple[Hashable, Hashable], None, None]: Parent-child pairs in a breadth-first
                traversal of the given graph, starting at the "source" node
        """

        # The code below was copied from GitHub and is under the 3-clause BSD license:
        #
        #  https://github.com/networkx/networkx/blob/main/networkx/algorithms/
        #      traversal/breadth_first_search.py
        #
        #       Code was not modified. It worked as written for both rx.PyGraph
        #       and a graph.Graph object
        #       with an RX graph embedded in it...
        #
        #       The only changes were removing optional parameters in the NX
        #       function for neighbors and depth_limit, since GerryChain
        #       does not need them.

        """Iterate over edges in a breadth-first search.

        The breadth-first search begins at `source` and enqueues the
        neighbors of newly visited nodes specified by the `neighbors`
        function.

        Args:
            G (RustworkX.PyGraph): RustworkX.PyGraph object (not a NetworkX graph).
            source (node): Starting node for the breadth-first search; this function
                iterates over only those edges in the component reachable from
                this node.
            neighbors (function): A function that takes a newly visited node of the
                graph as input and returns an *iterator* (not just a list) of nodes
                that are neighbors of that node with custom ordering. If not
                specified, this is just the ``G.neighbors`` method, but in general it
                can be any function that returns an iterator over some or all of the
                neighbors of a given node, in any order.
            depth_limit (int, optional): Specify the maximum search depth.
                Defaults to ``len(G)``.

        Yields:
            edge: Edges in the breadth-first search starting from `source`.

        Examples:
        >>> G = nx.path_graph(7)
        >>> list(nx.generic_bfs_edges(G, source=0))
        [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]
        >>> list(nx.generic_bfs_edges(G, source=2))
        [(2, 1), (2, 3), (1, 0), (3, 4), (4, 5), (5, 6)]
        >>> list(nx.generic_bfs_edges(G, source=2, depth_limit=2))
        [(2, 1), (2, 3), (1, 0), (3, 4)]

        The `neighbors` param can be used to specify the visitation order of each
        node's neighbors generically. In the following example, we modify the default
        neighbor to return *odd* nodes first:

        >>> def odd_first(n):
        ...     return sorted(G.neighbors(n), key=lambda x: x % 2, reverse=True)

        >>> G = nx.star_graph(5)
        >>> list(nx.generic_bfs_edges(G, source=0))  # Default neighbor ordering
        [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)]
        >>> list(nx.generic_bfs_edges(G, source=0, neighbors=odd_first))
        [(0, 1), (0, 3), (0, 5), (0, 2), (0, 4)]

        Notes:
        This implementation is from `PADS`_, which was in the public domain
        when it was first accessed in July, 2004.  The modifications
        to allow depth limits are based on the Wikipedia article
        "`Depth-limited-search`_".

        .. _PADS: http://www.ics.uci.edu/~eppstein/PADS/BFS.py
        .. _Depth-limited-search: https://en.wikipedia.org/wiki/Depth-limited_search
        """

        # Original NX code passed these in as optional parameters...
        neighbors = self.neighbors
        depth_limit = len(self)

        seen = {source}
        n = len(self)
        depth = 0
        next_parents_children = [(source, neighbors(source))]
        while next_parents_children and depth < depth_limit:
            this_parents_children = next_parents_children
            next_parents_children = []
            for parent, children in this_parents_children:
                for child in children:
                    # frm: avoid cycles - don't process a child twice...
                    if child not in seen:
                        seen.add(child)
                        # frm: add this node's children to list to be processed later...
                        next_parents_children.append((child, neighbors(child)))
                        yield (parent, child)
                if len(seen) == n:
                    return
            depth += 1

    def generic_bfs_successors_generator(
        self, root_node_id: Hashable
    ) -> Generator[tuple[Hashable, list[Hashable]], None, None]:
        """Yield BFS ``(parent, children)`` pairs starting from ``root_node_id``.

        Each yielded tuple contains a parent node and its children in breadth-first traversal order.

        Does a breadth-first traversal of the given graph, starting at the node specified by
        "root_node_id", and yields (in breadth-first order) a tuple consisting of each of the nodes
        traversed along with the children of that node.

        Args:
            root_node_id (Hashable): Node ID at which to start the BFS traversal.

        Returns:
            Generator[tuple[Hashable, list[Hashable]], None, None]: Parent and children pairs
                in breadth-first order, with the first parent specified by the "root_node_id"
        """
        # frm: Generate in sequence a tuple for the parent (node_id) and
        #       the children of that node (list of node_ids).
        parent = root_node_id
        children = []
        for p, c in self._generic_bfs_edges(root_node_id):
            # frm: parent-child pairs appear ordered by their parent, so
            #       we can collect all of the children for a node by just
            #       iterating through pairs until the parent changes.
            if p == parent:
                children.append(c)
                continue
            yield (parent, children)
            # new parent, so reset parent and children variables to
            # be the new parent (p) and a new children list containing
            # this first child (c), and continue looping
            children = [c]
            parent = p
        yield (parent, children)

    def generic_bfs_successors(self, root_node_id: Hashable) -> dict[Hashable, list[Hashable]]:
        """Return the BFS successors mapping for ``root_node_id``.

        The returned dictionary maps each parent node_id to a list of child node_ids.

        Does a breadth-first traversal of the given graph, starting at the node specified by
        "root_node_id", and returns a dict mapping parent node_ids to a list of the node_ids for
        that node's children.

        Args:
            root_node_id (Hashable): Node ID at which to start the BFS traversal.

        Returns:
            dict[Hashable, list[Hashable]]: Parent node IDs mapped to their
                node's children.
        """
        return dict(self.generic_bfs_successors_generator(root_node_id))

    def generic_bfs_predecessors(self, root_node_id: Hashable) -> dict[Hashable, Hashable]:
        """Return A dict mapping each node_id to the node_id of its parent node.

        Returns a dict mapping each node_id in the graph to its predecessor node_id where the
        parent/child relationship is created by doing a breadth-first traversal of the graph
        starting at the root_node_id.

        Note that this works for both NX and RX based Graph objects.

        Args:
            root_node_id (Hashable): Root node of the breadth-first traversal.

        Returns:
            dict[Hashable, Hashable]: Node IDs mapped to their parent node IDs.
        """
        # frm Note:  We had do implement our own, because the built-in RX version only worked
        #               for directed graphs.
        predecessors = []
        for s, t in self._generic_bfs_edges(root_node_id):
            predecessors.append((t, s))
        return dict(predecessors)

    def predecessors(self, root_node_id: Hashable) -> dict[Hashable, Hashable]:
        """Return A dict mapping each node_id to the node_id of its parent node.

        Returns a dict mapping each node_id in the graph to its predecessor node_id where the
        parent/child relationship is created by doing a breadth-first traversal of the graph
        starting at the root_node_id.

        Note that the description above is exactly the same description as the description for
        generic_bfs_predecessors().

        The only difference between this routine and generic_bfs_predecessors() is that this
        routine delegates to a built-in NetworkX routine in the case when the embedded graph object
        is NX-based. The assumption is that the built-in NetworkX implementation is faster.

        In the case of an RX-based graph, this code delegates to generic_bfs_predecessors().

        Args:
            root_node_id (Hashable): Root node of the breadth-first traversal.

        Returns:
            dict[Hashable, Hashable]: Node IDs mapped to their parent node IDs.
        """

        """
        frm: It took me a while to grok what predecessors() and successors()
        were all about.  In the end, it was simple - they are just the
        parents and the children of a tree that "starts" at the given root
        node.

        What took me a while to understand is that this effectively
        converts an undirected cyclic graph into a DAG.  What is clever is
        that as soon as it detects a cycle it stops traversing the graph.
        The other thing that is clever is that the DAG that is created
        either starts at the top or the bottom.  For successors(), the
        DAG starts at the top, so that the argument to successors() is
        the root of the tree.  However, in the case of predecessors()
        the argument to predecessors() is a leaf node, and the "tree"
        can have multiple "roots".

        In both cases, you can ask what the associated parent or
        children are of any node in the graph.  If you ask for the
        successors() you will get a list of the children nodes.
        If you ask for the predecessors() you will get the single
        parent node.

        I think that the successors() graph is deterministic (except
        for the order of the child nodes), meaning that for a given
        graph no matter what order you created nodes and added edges,
        you will get the same set of children for a given node.
        However, for predecessors(), there are many different
        DAGs that might be created depending on which edge the
        algorithm decides is the single parent.

        All of this is interesting, but I have not yet spent the
        time to figure out why it matters in the code.

        TODO: Code: predecessors(): Decide if it makes sense to have different implementations
              for NX and RX.  The code below has the original definition
              from the pre-RX codebase, but the code for RX will work
              for NX too - so I think that there is no good reason to
              have different code for NX. Maybe no harm, but on the other
              hand, it seems like a needless difference and hence more
              complexity...

        TODO: Performance: see if the performance of the built-in NX
              version is significantly better than the generic one.
        """

        if self._rx_graph is not None:
            return self.generic_bfs_predecessors(root_node_id)
        elif self._nx_graph is not None:
            return {a: b for a, b in networkx.bfs_predecessors(self._nx_graph, root_node_id)}
        else:
            raise TypeError(
                "Graph passed to 'predecessors()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def successors(self, root_node_id: Hashable) -> dict[Hashable, list[Hashable]]:
        """Return a dictionary mapping each node to a list of its children.

        Does a breadth-first traversal of the given graph, starting at the node specified by
        "root_node_id", and returns a dict mapping parent node_ids to a list of the node_ids for
        that node's children.

        Note that the above is the exact same description as the description for
        generic_bfs_successors(). In fact, for NX-based graphs, this routine just delegates to
        NetworkX for the result.

        The reason for the delegation to NetworkX is the presumption that the NX version would be
        faster - which may or may not actually be the case.

        Args:
            root_node_id (Hashable): Node ID at which to start the breadth-first
                traversal of the graph.

        Returns:
            dict[Hashable, list[Hashable]]: Nodes mapped to their children.
        """
        if self._rx_graph is not None:
            return self.generic_bfs_successors(root_node_id)
        elif self._nx_graph is not None:
            return {a: b for a, b in networkx.bfs_successors(self._nx_graph, root_node_id)}
        else:
            raise TypeError(
                "Graph passed to 'successors()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def minimum_spanning_tree_from_edge_weight(self, edge_weight_attribute_name: str) -> Graph:
        """Computes and returns the minimum spanning tree give the edge weights.

        This method computes and returns the minimum spanning tree give the edge weights. It
        returns a Graph object containing the miniumum spanning tree given the edge weights.

        Args:
            edge_weight_attribute_name (str): The name of the edge attribute containing the weight
                of the edge

        Returns:
            Graph: A Graph object containing the miniumum spanning tree given the edge weights.
        """

        # Note that the RX version of this function is MUCH faster than the NX version.

        if self._nx_graph is not None:
            nx_graph = self.get_nx_graph()
            spanning_tree = networkx.algorithms.tree.minimum_spanning_tree(
                nx_graph, algorithm="kruskal", weight=edge_weight_attribute_name
            )
            spanning_graph = Graph.from_networkx(spanning_tree)
            # nx.minimum_spanning_tree seeds its result by iterating this graph's nodes,
            # which is hash-ordered when this graph is a subgraph view; the tree spans
            # exactly our node set, so carry the canonical order over.
            spanning_graph._nx_node_order = self.nodes
        elif self._rx_graph is not None:
            rx_graph = self.get_rx_graph()

            def get_weight(edge_data: _AttributeDict) -> float:
                # function to get the weight of an edge from its data
                # This function is passed a dict with the data for the edge.
                return edge_data[edge_weight_attribute_name]

            spanning_tree = rustworkx.minimum_spanning_tree(rx_graph, get_weight)

            spanning_graph = Graph.from_rustworkx(spanning_tree)
        else:
            raise Exception("random_spanning_tree - bad kind of graph object")

        return spanning_graph

    def neighbors(self, node_id: Hashable) -> Sequence[Hashable]:
        """Return a sequence of neighbor node_ids.

        Return a sequence of the node_ids of the nodes that are neighbors of the given node - that
        is, all of the nodes that are directly connected to the given node by an edge.

        The result supports iteration (repeatedly), ``len()``, and indexing, but it is not
        guaranteed to be a ``list``. Callers that need list methods should wrap it in ``list()``.

        The neighbors are returned in a deterministic order. RX collects neighbors into a randomly
        seeded HashSet, so the raw ``rustworkx.NodeIndices`` order varies call to call; any seeded
        algorithm that maps RNG draws over neighbor order (a random walk, a BFS feeding a random
        choice) would otherwise be unreproducible.

        Args:
            node_id (Hashable): A node ID.

        Returns:
            Sequence[Hashable]: The neighboring node IDs.
        """
        if self._rx_graph is not None:
            return sorted(self._rx_graph.neighbors(cast(int, node_id)))
        elif self._nx_graph is not None:
            # NX returns a single-pass iterator, so it must be materialized here;
            # callers (and the FrozenGraph.neighbors lru_cache) expect a re-iterable result.
            return list(self._nx_graph.neighbors(node_id))
        else:
            raise TypeError(
                "Graph passed to 'neighbors()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def degree(self, node_id: Hashable) -> int:
        """Return the degree of the given node, that is, the number of other nodes directly.

        This method returns the degree of the given node, that is, the number of other nodes
        directly. It returns number of nodes directly connected to the given node.

        Args:
            node_id (Hashable): A node ID.

        Returns:
            int: Number of nodes directly connected to the given node
        """
        if self._rx_graph is not None:
            return self._rx_graph.degree(cast(int, node_id))
        elif self._nx_graph is not None:
            return self._nx_graph.degree(node_id)
        else:
            raise TypeError(
                "Graph passed to 'degree()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def node_data(self, node_id: Hashable) -> _AttributeDict:
        """Return the data dictionary that contains the given node's data.

        As docmented elsewhere, in GerryChain code before the conversion to RustworkX, users could
        access node data using the syntax:

        graph.nodes[node_id][attribute_name]

        This was because a GerryChain Graph object in that codebase was a subclass of
        NetworkX.Graph, and NetworkX was clever and implemented dict-like behavior for the syntax
        graph.nodes[]...

        This Python cleverness was not carried over to the RustworkX implementation, so in the
        current GerryChain Graph implementation users need to access node data using the syntax:

        graph.node_data(node_id)[attribute_name]

        Args:
            node_id (Hashable): A node ID.

        Returns:
            dict[str, Any]: The node's data.
        """

        if self._rx_graph is not None:
            return self._rx_graph[cast(int, node_id)]
        elif self._nx_graph is not None:
            return self._nx_graph.nodes[node_id]
        else:
            raise TypeError(
                "Graph passed to 'node_data()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def edge_data(self, edge_id: Hashable) -> _AttributeDict:
        """Return the data dictionary that contains the data for the given edge.

        Note that in NetworkX an edge_id can be almost anything, for instance, a string or even a
        tuple. However, in RustworkX, an edge_id is an integer. This method handles both kinds.

        Args:
            edge_id (Hashable): An edge ID.

        Returns:
            dict[str, Any]: The edge's data.
        """

        if self._rx_graph is not None:
            return self._rx_graph.get_edge_data_by_index(cast(int, edge_id))
        elif self._nx_graph is not None:
            return self._nx_graph.edges[cast(tuple[Hashable, Hashable], edge_id)]
        else:
            raise TypeError(
                "Graph passed to 'edge_data()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

        # # Sanity check - RX edges do not need to have a data dict for node data
        # #
        # # A GerryChain Graph object should always be constructed with a data dict
        # # for edge data, but it doesn't hurt to check.
        # if not isinstance(data_dict, dict):
        #     raise TypeError("graph.edge(): data for edge is not a dict")
        #
        # return data_dict

    # Note:  The two laplacian functions: laplacian_matrix() and
    # normalized_laplacian_matrix() are part of the Graph class primarily to
    # encapsulate all NetworkX dependencies in one place - this module.

    def laplacian_matrix(self) -> scipy.sparse.csr_array:
        """Return a SciPy sparse array containing the Laplacian matrix for the given graph.

        For more details on the Graph Laplacian matrix, please refer to -
        https://fanchung.ucsd.edu/research/cb/ch1.pdf -
        https://en.wikipedia.org/wiki/Laplacian_matrix

        Returns:
            scipy.sparse.csr_array: A SciPy sparse array containing the Laplacian matrix
        """
        # A local "gc" (as in GerryChain) version of the laplacian matrix

        if self._rx_graph is not None:
            rx_graph = self._rx_graph
            # 1. Get the adjacency matrix
            adj_matrix = rustworkx.adjacency_matrix(rx_graph)
            # 2. Calculate the degree matrix (simplified for this example)
            degree_matrix = numpy.diag([rx_graph.degree(node) for node in rx_graph.node_indices()])
            # 3. Calculate the Laplacian matrix
            np_laplacian_matrix = degree_matrix - adj_matrix
            # 4.  Convert the NumPy array to a scipy.sparse array
            laplacian_matrix = scipy.sparse.csr_array(np_laplacian_matrix)
        elif self._nx_graph is not None:
            nx_graph = self._nx_graph
            laplacian_matrix = networkx.laplacian_matrix(nx_graph)
        else:
            raise TypeError(
                "Graph passed into laplacian_matrix() is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

        return laplacian_matrix

    def normalized_laplacian_matrix(self) -> scipy.sparse.csr_array:
        """Return a SciPy sparse array containing the normalized Laplacian matrix for the given.

        graph. For more details on the normalized Graph Laplacian matrix, please refer to -
        https://fanchung.ucsd.edu/research/cb/ch1.pdf -
        https://en.wikipedia.org/wiki/Laplacian_matrix#Laplacian_matrix_normalization_2

        Returns:
            scipy.sparse.csr_array: A SciPy sparse array containing the normalized Laplacian matrix
        """

        def create_scipy_sparse_array_from_rx_graph(
            rx_graph: rustworkx.PyGraph[_AttributeDict, _AttributeDict],
        ) -> scipy.sparse.coo_matrix:
            """Create a scippy.sparce.coo_matrix from the given RX graph.

            This is needed in the code below to compute the normalized laplacian for the graph.

            Args:
                rx_graph (rustworkx.PyGraph): The RustworkX graph object from which to create the
                    sparse array.

            Returns:
                scipy.sparse.coo_matrix: A SciPy sparse matrix
            """
            num_nodes = rx_graph.num_nodes()

            rows = []
            cols = []
            data = []

            for u, v in rx_graph.edge_list():
                rows.append(u)
                cols.append(v)
                data.append(1)  # simple adjacency matrix, so just 1 not weight attribute

                # rx_graph.edge_list() yields each undirected edge only once, but the
                # adjacency matrix of an undirected graph is symmetric, so we must add the
                # mirrored entry as well. Skip self-loops so the diagonal is not double counted.
                if u != v:
                    rows.append(v)
                    cols.append(u)
                    data.append(1)

            sparse_array = scipy.sparse.coo_matrix(
                (data, (rows, cols)), shape=(num_nodes, num_nodes)
            )

            return sparse_array

        if self._rx_graph is not None:
            rx_graph = self._rx_graph
            """
            The following is code copied from the networkx linalg file, laplacianmatrix.py
            for normalized_laplacian_matrix.  Below this code has been modified to work for
            gerrychain (with an RX-based Graph object)

            import numpy as np
            import scipy as sp

            if nodelist is None:
                nodelist = list(G)
            A = nx.to_scipy_sparse_array(G, nodelist=nodelist, weight=weight, format="csr")
            n, _ = A.shape
            diags = A.sum(axis=1)
            D = sp.sparse.dia_array((diags, 0), shape=(n, n)).tocsr()
            L = D - A
            with np.errstate(divide="ignore"):
                diags_sqrt = 1.0 / np.sqrt(diags)
            diags_sqrt[np.isinf(diags_sqrt)] = 0
            DH = sp.sparse.dia_array((diags_sqrt, 0), shape=(n, n)).tocsr()
            return DH @ (L @ DH)

            """

            # The RX result is validated against networkx.normalized_laplacian_matrix()
            # (the reference implementation used by the NX path) in
            # tests/test_laplacian.py.

            A = create_scipy_sparse_array_from_rx_graph(rx_graph)
            n, _ = A.shape  # shape() => dimensions of the array (rows, cols), so n = num_rows
            diags = A.sum(axis=1)  # sum of values in each row => column vector
            diags = diags.T  # convert to a row vector / 1D array
            D = scipy.sparse.dia_array((diags, [0]), shape=(n, n)).tocsr()
            L = D - A
            with numpy.errstate(divide="ignore"):
                diags_sqrt = 1.0 / numpy.sqrt(diags)
            diags_sqrt[numpy.isinf(diags_sqrt)] = 0
            DH = scipy.sparse.dia_array((diags_sqrt, 0), shape=(n, n)).tocsr()
            normalized_laplacian = DH @ (L @ DH)
            return normalized_laplacian

        elif self._nx_graph is not None:
            nx_graph = self._nx_graph
            laplacian_matrix = networkx.normalized_laplacian_matrix(nx_graph)
        else:
            raise TypeError(
                "Graph passed into normalized_laplacian_matrix() is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

        return laplacian_matrix

    def is_connected(self) -> bool:
        """Return whether the (undirected) graph is connected.

        Delegates to the backend's native connectivity routine - ``rustworkx.is_connected`` for an
        RX graph, ``networkx.is_connected`` for an NX graph - which are faster than hand-rolled
        Python traversal.

        A graph with 0 or 1 nodes is treated as trivially connected. This also guards the
        backend calls, both of which raise on an empty graph (rustworkx ``NullGraph`` /
        networkx ``NetworkXPointlessConcept``).

        Returns:
            bool: True if the graph is connected (or has at most one node).
        """
        if self._rx_graph is not None:
            if self._rx_graph.num_nodes() <= 1:
                return True
            return rustworkx.is_connected(self._rx_graph)
        elif self._nx_graph is not None:
            if self._nx_graph.number_of_nodes() <= 1:
                return True
            return networkx.is_connected(self._nx_graph)
        else:
            raise TypeError(
                "Graph passed to 'is_connected()' is neither a networkx-based graph nor a "
                "rustworkx-based graph."
            )

    def is_node_set_connected(self, nodes: Iterable[Hashable]) -> bool:
        """Return whether the given set of nodes induces a connected subgraph of this graph.

        This is a fast path for connectivity checks. It hands the node set straight to the
        backend's subgraph constructor and runs the native connectivity routine on the result,
        skipping the ``Graph`` wrapper and the node-id translation maps that ``subgraph()``
        builds - none of which are needed to answer a yes/no connectivity question.

        A set of 0 or 1 nodes is treated as trivially connected, mirroring ``is_connected()``.

        Args:
            nodes (Iterable[Hashable]): Node IDs to check.

        Returns:
            bool: True if the nodes induce a connected subgraph (or there are at most one
                of them).
        """
        if not isinstance(nodes, list):
            nodes = list(nodes)
        if len(nodes) <= 1:
            return True

        if self._rx_graph is not None:
            return rustworkx.is_connected(self._rx_graph.subgraph(cast(list[int], nodes)))
        elif self._nx_graph is not None:
            return networkx.is_connected(self._nx_graph.subgraph(nodes))
        else:
            raise TypeError(
                "Graph passed to 'is_node_set_connected()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

    def subgraphs_for_connected_components(self) -> list[Graph]:
        """Create and return a list of subgraphs for each set of nodes in the given graph that are.

        connected. Note that a connected graph is one in which there is a path from every node in
        the graph to every other node in the graph.

        Note also that each of the subgraphs returned is a maximal subgraph of connected
        components, meaning that there is no other larger subgraph of connected components that
        includes it as a subset.

        Returns:
            list['Graph']: A list of "maximal" subgraphs each of which contains nodes that are
                connected.
        """

        if self._rx_graph is not None:
            rx_graph = self.get_rx_graph()
            subgraphs = [self.subgraph(nodes) for nodes in rustworkx.connected_components(rx_graph)]
        elif self._nx_graph is not None:
            nx_graph = self.get_nx_graph()
            subgraphs = [self.subgraph(nodes) for nodes in networkx.connected_components(nx_graph)]
        else:
            raise TypeError(
                "Graph passed to 'subgraphs_for_connected_components()' is "
                "neither a networkx-based graph nor a rustworkx-based graph"
            )

        return subgraphs

    def num_connected_components(self) -> int:
        """Return the number of connected components.

        Note: A connected component is a maximal subgraph where every vertex is reachable from
        every other vertex in that same subgraph. In a graph that is not fully connected, connected
        components are the separate, distinct "islands" of connected nodes. Every node in a graph
        belongs to exactly one connected component.

        Returns:
            int: The number of connected components
        """

        # frm: TODO: Performance:  num_connected_components(): do both NX and RX have builtins
        # for this?
        #
        # NetworkX and RustworkX both have a routine number_connected_components().
        # I am guessing that it is more efficient to call these than it is
        # to construct the connected components and then determine how many
        # of them there are.
        #
        # So - should be a simple issue of trying it and running tests, but
        # I will do that another day...

        if self._rx_graph is not None:
            rx_graph = self.get_rx_graph()
            connected_components = rustworkx.connected_components(rx_graph)
        elif self._nx_graph is not None:
            nx_graph = self.get_nx_graph()
            connected_components = list(networkx.connected_components(nx_graph))
        else:
            raise TypeError(
                "Graph passed to 'num_connected_components()' is neither "
                "a networkx-based graph nor a rustworkx-based graph"
            )

        num_cc = len(connected_components)
        return num_cc

    def is_a_tree(self) -> bool:
        """Return whether the current graph is a tree - meaning that it is connected and that it.

        This method returns whether the current graph is a tree - meaning that it is connected and
        that it. It returns whether the current graph is a tree.

        Returns:
            bool: Whether the current graph is a tree
        """

        # Note: is_a_tree() is only called in a test (test_tree.py)
        #
        # However, it does no harm, and it might be useful, perhaps...

        if self._rx_graph is not None:
            rx_graph = self.get_rx_graph()
            num_nodes = rx_graph.num_nodes()
            num_edges = rx_graph.num_edges()

            # Condition 1: Check if the number of edges is one less than the number of nodes
            if num_edges != num_nodes - 1:
                return False

            # Condition 2: Check for connectivity (and implicitly, acyclicity if E = V-1)
            # A graph with V-1 edges and no cycles must be connected.
            # A graph with V-1 edges and connected must be acyclic.

            # We can check connectivity by ensuring there's only one connected component.
            connected_components = rustworkx.connected_components(rx_graph)
            if len(connected_components) != 1:
                return False

            return True
        elif self._nx_graph is not None:
            nx_graph = self.get_nx_graph()
            return networkx.is_tree(nx_graph)
        else:
            raise TypeError(
                "Graph passed to 'is_a_tree()' is neither a "
                "networkx-based graph nor a rustworkx-based graph"
            )


def _add_boundary_perimeters_to_nx_graph(
    nx_graph: networkx.Graph[Hashable, _AttributeDict, _AttributeDict],
    geometries: gp.GeoSeries,
) -> None:
    """Computes the "boundary perimeter" which is a measure of how much of the node's perimeter is.

    Computes the "boundary perimeter" which is a measure of how much of the node's perimeter is on
    the external boundary of the graph.

    Conceptually this is easy - consider a geographical map of a state and then consider all of the
    counties in the state. Some of the counties will touch other states (or perhaps the ocean or
    another country) while other counties will only touch other counties in the state. One can then
    ask how much of the perimeter of each county touches something outside the state. This is
    exactly what a "boundary perimeter" denotes for a graph, except that instead a county, the unit
    of interest is a node.

    Note that the graph passed in is a NetworkX.Graph object, which is a bit odd, and which should
    probably be changed in the future to be a GerryChain Graph object, but since this routine is
    useful for building a graph, having it operate on a NetworkX graph seemed reasonable.

    However, the fact that the graph passed in is a NetworkX.Graph object means that one might need
    to reach down inside a GerryChain.Graph object to get access to the embedded NetworkX.Graph via
    get_nx_graph().

    Args:
        nx_graph (networkx.Graph): NetworkX graph
        geometries (gp.GeoSeries): GeoSeries containing geometry
            information.

    """

    if not (isinstance(nx_graph, networkx.Graph)):
        raise TypeError(
            "Graph passed into _add_boundary_perimeters_to_nx_graph() is not a networkx graph"
        )

    prepared_boundary = prep(unary_union(geometries).boundary)

    boundaries = cast(gp.GeoSeries, geometries.boundary)
    boundary_nodes = boundaries.apply(prepared_boundary.intersects)

    for node in nx_graph:
        is_boundary = bool(boundary_nodes.loc[node])
        nx_graph.nodes[node]["boundary_node"] = is_boundary
        if is_boundary:
            geometry = cast(BaseGeometry, geometries.loc[node])
            total_perimeter = geometry.boundary.length
            shared_perimeter = sum(
                neighbor_data["shared_perim"] for neighbor_data in nx_graph[node].values()
            )
            boundary_perimeter = total_perimeter - shared_perimeter
            nx_graph.nodes[node]["boundary_perim"] = boundary_perimeter


def check_dataframe(df: pd.DataFrame) -> None:
    """Check a dataframe for missing values.

    This function scans each column and warns if any NA values are present.

    Raises:
        UserWarning: if the dataframe has any NA values.
    """
    for column in df.columns:
        if sum(df[column].isna()) > 0:
            warnings.warn(f"NA values found in column {column}!")


def remove_geometries(data: _AdjacencyData) -> None:
    """Remove geometry attributes from NetworkX adjacency data because they are not serializable.

    Note:
        Mutates the ``data`` object. Does nothing if no geometry attributes are found.

    Args:
        data (_AdjacencyData): an adjacency data object (returned by
            `networkx.readwrite.json_graph.adjacency_data`)

    """
    for node in data["nodes"]:
        bad_keys = []
        for key in node:
            # having a ``__geo_interface__``` property identifies the object
            # as being a ``shapely`` geometry object
            if hasattr(node[key], "__geo_interface__"):
                bad_keys.append(key)
        for key in bad_keys:
            del node[key]


def convert_geometries_to_geojson(data: _AdjacencyData) -> None:
    """Convert geometry attributes in a NetworkX adjacency data to GeoJSON for serialization.

    Note:
        Mutates the ``data`` object and does nothing if no geometry attributes are found.

    Args:
        data (_AdjacencyData): an adjacency data object (returned by
            `networkx.readwrite.json_graph.adjacency_data`)

    """
    for node in data["nodes"]:
        for key in node:
            # having a ``__geo_interface__``` property identifies the object
            # as being a ``shapely`` geometry object
            if hasattr(node[key], "__geo_interface__"):
                # The ``__geo_interface__`` property is essentially GeoJSON.
                # This is what `geopandas.GeoSeries.to_json` uses under
                # the hood.
                node[key] = cast(_GeoInterface, node[key]).__geo_interface__


class FrozenGraph:
    """
    Represents an immutable graph to be partitioned. It is based off Graph.

    This speeds up chain runs and prevents having to deal with cache invalidation issues.
    This class behaves slightly differently than Graph or Graph.

    Not intended to be a part of the public API.

    Attributes:
        graph (Graph): The underlying graph.
        size (int): The number of nodes in the graph.
    Note:
        The class uses `__slots__` for improved memory efficiency.
    """

    # Note: NetworkX has a way to "freeze" a graph so that calls to add nodes
    # or edges will fail, but RustworkX does not have a similar mechanism, so
    # we cannot actually "freeze" an RX-based Graph (which is what we will typically
    # have after creating a Partition object).
    #
    # This means that we cannot prevent a user from going under the covers and
    # changing an RX-based graph, but there are no functions defined for the
    # GerryChain Graph object to add nodes, so it seems reasonable to just assume
    # that the graph will not be modified.
    #

    # Note: __slots__ means FrozenGraph instances have no __dict__, so we cannot use
    # functools.cached_property (which caches into the instance __dict__). The cached
    # node_indices / edge_indices values are stored in dedicated slots instead.
    __slots__ = ["graph", "size", "_node_indices", "_edge_indices"]

    def __init__(self, graph: Graph) -> None:
        """Initialize a FrozenGraph from a Graph.

        Args:
            graph (Graph): The mutable Graph to be converted into an immutable graph

        """

        self.graph = graph
        self._node_indices: frozenset[Hashable] | None = None
        self._edge_indices: frozenset[Hashable] | None = None

        all_node_ids = self.graph.node_indices
        self.size = len(all_node_ids)

        # Validate that the node_id maps contain mappings for all nodes in the graph.
        #
        # This is pure defensive coding - it should never happen, but better safe...
        #
        if not all_node_ids.issubset(self.graph._node_id_to_parent_node_id_map.keys()):
            raise Exception(
                "FrozenGraph.__init__(): _node_id_to_parent_node_id_map does not contain all nodes"
            )
        if not all_node_ids.issubset(self.graph._node_id_to_original_nx_node_id_map.keys()):
            raise Exception(
                "FrozenGraph.__init__(): _node_id_to_original_nx_node_id_map does not contain all nodes"
            )

    def __len__(self) -> int:
        """Returns the number of nodes in the graph.

        Returns:
            int: Number of nodes in the graph
        """
        return self.size

    def __getattr__(self, __name: str) -> Any:
        # Don't delegate dunder/introspection names (e.g. __deepcopy__, __getstate__,
        # __test__) to the wrapped graph - that would leak copy/pickle/introspection
        # probes into it. Let normal Python fallback handle them by raising here.
        if __name.startswith("__") and __name.endswith("__"):
            raise AttributeError(__name)
        # 'graph' is a slot; fetch it via object.__getattribute__ so that an
        # as-yet-unset 'graph' (e.g. during __init__) raises AttributeError here
        # instead of recursing back into __getattr__.
        if __name == "graph":
            raise AttributeError(__name)
        return getattr(object.__getattribute__(self, "graph"), __name)

    def __getitem__(self, node_id: Hashable) -> Mapping[Hashable, _AttributeDict]:
        return self.graph[node_id]

    def __iter__(self) -> Iterator[Hashable]:
        yield from self.node_indices

    @functools.lru_cache(16384)
    def neighbors(self, n: Hashable) -> Sequence[Hashable]:
        return self.graph.neighbors(n)

    @property
    def node_indices(self) -> frozenset[Hashable]:
        # Cached into a slot (see __slots__ note) since the graph is immutable. Store a
        # frozenset so a caller can't mutate the shared cached object in place (e.g. via `-=`).
        if self._node_indices is None:
            self._node_indices = frozenset(self.graph.node_indices)
        return self._node_indices

    @property
    def edge_indices(self) -> frozenset[Hashable]:
        if self._edge_indices is None:
            self._edge_indices = frozenset(self.graph.edge_indices)
        return self._edge_indices

    @functools.lru_cache(16384)
    def degree(self, n: Hashable) -> int:
        return self.graph.degree(n)

    def subgraph(self, nodes: Iterable[Hashable]) -> FrozenGraph:
        return FrozenGraph(self.graph.subgraph(nodes))
