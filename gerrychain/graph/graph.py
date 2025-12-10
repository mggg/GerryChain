"""
This module provides tools for working with graphs in the context of geographic data.
It extends the functionality of the NetworkX library, adding support for spatial data structures,
geographic projections, and serialization to and from JSON format.

This module is designed to be used in conjunction with geopandas, shapely, and pandas libraries,
facilitating the integration of graph-based algorithms with geographic information systems (GIS).

Note:
This module relies on NetworkX, pandas, and geopandas, which should be installed and
imported as required.

TODO: Documentation: Update top-level documentation for graph.py
"""

import functools
import json
from typing import Any
import warnings

import networkx
from networkx.classes.function import frozen
from networkx.readwrite import json_graph
import pandas as pd

import rustworkx

from .adjacency import neighbors
from .geo import GeometryError, invalid_geometries, reprojected

# frm: codereview note: removed type hints that are now baked into Python 
from typing import Iterable, Optional, Generator, Union

import geopandas as gp
from shapely.ops import unary_union
from shapely.prepared import prep

import numpy 
import scipy

# frm: TODO: Refactor: Move json_serialize() closer to its use.
#
# It should not be the first thing someone sees when looking at this code...
#
def json_serialize(input_object: Any) -> Optional[int]:
    """
    This function is used to handle one of the common issues that
    appears when trying to convert a pandas dataframe into a JSON
    serializable object. Specifically, it handles the issue of converting
    the pandas int64 to a python int so that JSON can serialize it.
    This is specifically used so that we can write graphs out to JSON
    files.

    :param input_object: The object to be converted
    :type input_object: Any (expected to be a pd.Int64Dtype)

    :returns: The converted pandas object or None if input is not of type
        pd.Int64Dtype
    :rtype: Optional[int]
    """
    if pd.api.types.is_integer_dtype(input_object):  # handle int64
        return int(input_object)

    return None

class Graph:
    """
    frm TODO: Documentation:  Clean up this documentation

    frm: this class encapsulates / hides the underlying graph which can either be a
    NetworkX graph or a RustworkX graph.  The intent is that it provides the same
    external interface as a NetworkX graph (for all of the uses that GerryChain cares
    about, at least) so that legacy code that operated on NetworkX based Graph objects
    can continue to work unchanged.

    When a graph is added to a partition, however, the NX graph will be converted into
    an RX graph and the NX graph will become unaccessible to the user.  The RX graph
    may also be "frozen" the way the NX graph was "frozen" in the legacy code, but we
    have not yet gotten that far in the implementation.

    It is not clear whether the code that does the heavy lifting on partitions will 
    need to use the old NX syntax or whether it will be useful to allow unfettered
    access to the RX graph so that RX code can be used in these modules.  TBD...


    """

    # Note: This class cannot have a constructor - because there is code that assumes
    #       that it can use the default constructor to create instances of it.
    #       That code is buried deep in non GerryChain code, so I don't really understand
    #       what it is doing, but the assignment of nx_graph and rx_graph class attributes/members
    #       needs to happen in the "from_xxx()" routines.

    # frm: TODO: Documentation:    Add documentation for new data members I am adding:
    #               _nx_graph, _rx_graph, _node_id_to_parent_node_id_map, _is_a_subgraph
    #               _node_id_to_original_nx_node_id_map
    #                   => used to recreate NX graph from an RX graph and also 
    #                      as an aid for testing

    @classmethod
    def from_networkx(cls, nx_graph: networkx.Graph) -> "Graph":
        """
        Create a :class:`Graph` from a NetworkX.Graph object

        This supports the use case of users creating a graph using NetworkX 
        which is convenient - both for users of the previous implementation of
        a GerryChain object which was a subclass of NetworkX.Graph and for 
        users more generally who are familiar with NetworkX.

        Note that most users will not ever call this function directly,
        because they can create a GerryChain Partition object directly
        from a NetworkX graph, and the Partition initialization code 
        will use this function to convert the NetworkX graph to a 
        GerryChain Graph object.

        :param nx_graph: A NetworkX.Graph object with node and edge data
            to be converted into a GerryChain Graph object.
        :type nx_graph: networkx.Graph

        :returns: ...text...
        :rtype: <type>
        """
        graph = cls()
        graph._nx_graph = nx_graph
        graph._rx_graph = None
        graph._is_a_subgraph = False        # See comments on RX subgraph issues.
        # Maps node_ids in the graph to the "parent" node_ids in the parent graph.
        # For top-level graphs, this is just an identity map 
        graph._node_id_to_parent_node_id_map = {node_id: node_id for node_id in graph.node_indices}   
        # Maps node_ids in the graph to the "original" node_ids in parent graph.
        # For top-level graphs, this is just an identity map 
        graph._node_id_to_original_nx_node_id_map = {node_id: node_id for node_id in graph.node_indices}   
        graph.nx_to_rx_node_id_map = None   # only set when an NX based graph is converted to be an RX based graph
        return graph
    
    @classmethod
    def from_rustworkx(cls, rx_graph: rustworkx.PyGraph) -> "Graph":
        """
        <Overview text for what the function does>

        Create a :class:`Graph` from a RustworkX.PyGraph object

        There are three primary use cases for this routine: 
        1) converting an NX-based Graph to be an RX-based 
        Graph, 2) creating a subgraph of an RX-based Graph, and 
        3) creating a Graph whose node_ids do not need to be 
        mapped to some previous graph's node_ids.

        In a little more detail: 

        1) A typical way to use GerryChain is to create a graph 
        using NetworkX functionality and to then rely on the 
        initialization code in the Partition class to create 
        an RX-based Graph object.  That initialization code
        constructs a RustworkX PyGraph and then uses this 
        routine to create an RX-based Graph object, and it then
        creates maps from the node_ids of the resulting RX-based
        Graph back to the original NetworkX.Graph's node_ids.

        2) When creating a subgraph of a RustworkX PyGraph 
        object, the node_ids of the subgraph are (in general) 
        different from those of the parent graph.  So we 
        create a mapping from the subgraph's node_ids to the 
        node_ids of the parent.  The subgraph() routine 
        creates a RustworkX PyGraph subgraph, then uses this
        routine to create an RX-based Graph using that subgraph,
        and it then creates the mapping of subgraph node_ids
        to the parent (RX) graph's node_ids.

        3) In those cases where no node_id mapping is needed
        this routine provides a simple way to create an 
        RX-based GerryChain graph object.

        :param rx_graph: a RustworkX PyGraph object
        :type rx_graph: rustworkx.PyGraph

        :returns: a GerryChain Graph object with an embedded RustworkX.PyGraph object
        :rtype: "Graph"
        """

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
         
        for node_id in rx_graph.node_indices():
            data_dict = rx_graph[node_id]
            if not isinstance(data_dict, dict):
                # Unrecoverable error - see above...
                raise Exception("from_rustworkx(): RustworkX graph does not have node_data dictionary")

        for edge_id in rx_graph.edge_indices():
            data_dict = rx_graph.get_edge_data_by_index(edge_id)
            if data_dict is None:
                # Create an empty dict for edge_data
                graph.update_edge_by_index(edge_id, {})
            if not isinstance(data_dict, dict):
                # Create a new dict with the existing edge_data as an item
                graph.update_edge_by_index(edge_id, {"__original_rx_edge_data": data_dict})

        graph = cls()   
        graph._rx_graph = rx_graph
        graph._nx_graph = None
        graph._is_a_subgraph = False        # See comments on RX subgraph issues.

        # frm: TODO: Documentation: from_rustworkx(): Make these comments more coherent
        #
        # Instead of these very specific comments, just say that at this 
        # point, we don't know whether the graph is derived from NX, is a
        # subgraph, or is something that can stand alone, so the maps are
        # all identity maps.  It is responsibility of callers to reset the
        # maps if that is appropriate...

        # Maps node_ids in the graph to the "parent" node_ids in the parent graph.
        # For top-level graphs, this is just an identity map 
        graph._node_id_to_parent_node_id_map = {node_id: node_id for node_id in graph.node_indices}   

        # This routine assumes that the rx_graph was not derived from an "original" NX
        # graph, so the RX node_ids are considered to be the "original" node_ids and 
        # we create an identity map - each node_id maps to itself as the "original" node_id
        #
        # If this routine is used for an RX-based Graph that was indeed derived from an
        # NX graph, then it is the responsibility of the caller to set 
        # the _node_id_to_original_nx_node_id_map appropriately.
        graph._node_id_to_original_nx_node_id_map = {node_id: node_id for node_id in graph.node_indices}   

        # only set when an NX based graph is converted to be an RX based graph
        graph.nx_to_rx_node_id_map = None   

        return graph

    def to_networkx_graph(self) -> networkx.Graph:
        """
        Create a NetworkX.Graph object that has the same nodes, edges, 
        node_data, and edge_data as the GerryChain Graph object.

        The intended purpose of this routine is to allow a user to
        run a MarkovChain - which uses an embedded RustworkX graph
        and then extract an equivalent version of that graph with all
        of its data as a NetworkX.Graph object - in order to use
        NetworkX routines to access and manipulate the graph.

        In short, this routine allows users to use NetworkX 
        functionality on a graph after running a MarkovChain.

        If the GerryChain graph object is NX-based, then this 
        routine merely returns the embedded NetworkX.Graph object.

        :returns: A NetworkX.Graph object that is equivalent to the 
            GerryChain Graph object (nodes, edges, node_data, edge_data)
        :rtype: networkx.Graph
        """
        if self.is_nx_graph():
            return self.get_nx_graph()
        
        if not self.is_rx_graph():
            raise TypeError(
              "Graph passed to 'to_networkx_graph()' must be a rustworkx graph"
            )

        # We have an RX-based Graph, and we want to create a NetworkX Graph object
        # that has all of the node data and edge data, and which has the
        # node_ids and edge_ids of the original NX graph.
        #
        # Original node_ids are those that were used in the original NX
        # Graph used to create the RX-based Graph object.
        #

        # Confirm that this RX based graph was derived from an NX graph...
        if self._node_id_to_original_nx_node_id_map == None:
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
            edge_0_original_nx_node_id = self.original_nx_node_id_for_internal_node_id(edge_0_node_id)
            edge_1_original_nx_node_id = self.original_nx_node_id_for_internal_node_id(edge_1_node_id)
            edge_payload = rx_graph.get_edge_data_by_index(edge_id)
            # Add edges and edge data using the original node_ids
            # as the names/IDs for the nodes that make up the edge
            edge_data.append({"source": edge_0_original_nx_node_id, "target": edge_1_original_nx_node_id, **edge_payload})

        # Create Pandas DataFrames
    
        nodes_df = pd.DataFrame(node_data)
        edges_df = pd.DataFrame(edge_data)

        # Create a NetworkX Graph object from the edges_df, using
        # "source", and "tartet" to define edge node_ids, and adding
        # all attribute data (True).
        nx_graph = networkx.from_pandas_edgelist(edges_df, 'source', 'target', True, networkx.Graph)

        # Add all of the node_data, using the "node_name" attr as the NX Graph node_id
        nodes_df = nodes_df.set_index('node_name')
        networkx.set_node_attributes(nx_graph, nodes_df.to_dict(orient='index'))

        return nx_graph

    # frm: TODO: Refactoring: Create a defined type name "node_id" to use instead of "Any"
    #
    # This is purely cosmetic, but it would provide an opportunity to add a comment that
    # talked about NX node_ids vs. RX node_ids and hence why the type for a node_id is
    # a vague "Any"...

    def original_nx_node_id_for_internal_node_id(self, internal_node_id: Any) -> Any:
        """
        Translate a node_id to its "original" node_id.

        :param internal_node_id: A node_id to be translated
        :type internal_node_id: Any

        :returns: A translated node_id
        :rtype: Any
        """
        return self._node_id_to_original_nx_node_id_map[internal_node_id]

    # frm: TODO: Testing: Create a test for this routine
    def original_nx_node_ids_for_set(self, set_of_node_ids: set[Any]) -> Any:
        """
        Translate a set of node_ids to their "original" node_ids.

        :param set_of_node_ids: A set of node_ids to be translated
        :type set_of_node_ids: set[Any]

        :returns: A set of translated node_ids
        :rtype: set[Any]
        """
        _node_id_to_original_nx_node_id_map = self._node_id_to_original_nx_node_id_map 
        new_set = {_node_id_to_original_nx_node_id_map[node_id] for node_id in set_of_node_ids}
        return new_set

    # frm: TODO: Testing: Create a test for this routine
    def original_nx_node_ids_for_list(self, list_of_node_ids: list[Any]) -> list[Any]:
        """
        Translate a list of node_ids to their "original" node_ids.

        :param list_of_node_ids: A list of node_ids to be translated
        :type list_of_node_ids: list[Any]

        :returns: A list of translated node_ids
        :rtype: list[Any]
        """
        # Utility routine to quickly translate a set of node_ids to their original node_ids
        _node_id_to_original_nx_node_id_map = self._node_id_to_original_nx_node_id_map 
        new_list = [_node_id_to_original_nx_node_id_map[node_id] for node_id in list_of_node_ids]
        return new_list
    
    def internal_node_id_for_original_nx_node_id(self, original_nx_node_id: Any) -> Any:
        """
        Discover the "internal" node_id in the current GerryChain graph
        that corresponds to the "original" node_id in the top-level
        graph (presumably an NX-based graph object). 

        This was originally created to facilitate testing where it was
        convenient to express the test success criteria in terms of
        "original" node_ids, but the actual test needed to be made
        using the "internal" (RX) node_ids.
        
        :param original_nx_node_id: The "original" node_id 
        :type original_nx_node_id: Any

        :returns: The corresponding "internal" node_id
        :rtype: Any
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
          v: k for k,v in self._node_id_to_original_nx_node_id_map.items()
        }
        return orignal_node_id_to_internal_node_id_map[original_nx_node_id]

    def verify_graph_is_valid(self) -> bool:
        """
        Verify that the graph is valid.

        This may be overkill, but the idea is that at least in 
        development mode, it would be prudent to check periodically 
        to see that the graph data structure has not been corrupted.

        :returns: True if the graph is deemed valid
        :rtype: bool
        """

        # frm: TODO: Performance:  Only check verify_graph_is_valid() in development.
        #
        # For now, in order to assess performance differences between NX and RX
        # I will just return True...
        return True


        # Sanity check - this is where to add additional sanity checks in the future.

        # frm: TODO: Code: Enhance verify_graph_is_valid to do more...

        # frm: TODO: Performance:  verify_graph_is_valid() is expensive - called a lot
        #
        # Come up with a way to run this in "debug mode" - that is, while in development/testing
        # but not in production.  It actually accounted for 5% of runtime...

        # Checks that there is one and only one graph
        if not (
            (self._nx_graph is not None and self._rx_graph is None)
            or (self._nx_graph is None and self._rx_graph is not None)
           ):
            raise Exception("Graph.verify_graph_is_valid(): graph not properly configured")

    # frm: TODO: Performance:  is_nx_graph() and is_rx_graph() are expensive.
    #
    # Not all of the calls on these routines are needed in production - some are just
    # sanity checking.  Find a way to NOT run this code when in production.

    # frm: TODO: Refactoring:  Reorder these following routines in sensible order

    def is_nx_graph(self) -> bool:
        """
        Determine if the graph is NX-based

        :rtype: bool
        """
        # frm: TODO: Performance:  Only check graph_is_valid() in production
        #
        # Find a clever way to only run this code in development.  Commenting it out for now...
        #     self.verify_graph_is_valid()
        return self._nx_graph is not None

    def get_nx_graph(self) -> networkx.Graph:
        """
        Return the embedded NX graph object

        :rtype: networkx.Graph
        """
        if not self.is_nx_graph():
            raise TypeError(
              "Graph passed to 'get_nx_graph()' must be a networkx graph"
            )
        return self._nx_graph

    def get_rx_graph(self) -> rustworkx.PyGraph:
        """
        Return the embedded RX graph object

        :rtype: rustworkx.PyGraph
        """
        if not self.is_rx_graph():
            raise TypeError(
              "Graph passed to 'get_rx_graph()' must be a rustworkx graph"
            )
        return self._rx_graph

    def is_rx_graph(self) -> bool:
        """
        Determine if the graph is RX-based

        :rtype: bool
        """
        # frm: TODO: Performance:  Only check graph_is_valid() in production
        #
        # Find a clever way to only run this code in development.  Commenting it out for now...
        #     self.verify_graph_is_valid()
        return self._rx_graph is not None

    def convert_from_nx_to_rx(self) -> "Graph":
        """
        Convert an NX-based graph object to be an RX-based graph object.

        The primary use case for this routine is support for users 
        constructing a graph using NetworkX functionality and then 
        converting that NetworkX graph to RustworkX when creating a
        Partition object.


        :returns: An RX-based graph that is "the same" as the given NX-based graph
        :rtype: "Graph"
        """

        # Note that in both cases in the if-stmt below, the nodes are not copied.
        # This is arguably dangerous, but in our case I think it is OK.  Stated 
        # differently, the actual node data (the dictionaries) in the original 
        # graph (self) will be reused in the returned graph - either because we
        # are just returning the same graph (if it is already based on rx.PyGraph)
        # or if we are converting it from NX.
        #
        self.verify_graph_is_valid()
        if self.is_nx_graph():

            if (self._is_a_subgraph):
                # This routine is intended to be used in exactly one place - in converting
                # an NX based Graph object to be RX based when creating a Partition object.
                # In the future, it might become useful for other reasons, but until then
                # to guard against careless uses, the code will insist that it not be a subgraph.

                # frm: TODO: Documentation:  Add a comment about the intended use of this routine to its 
                #               overview comment above.
                raise Exception("convert_from_nx_to_rx(): graph to be converted is a subgraph")

            nx_graph = self._nx_graph
            rx_graph = rustworkx.networkx_converter(nx_graph, keep_attributes=True)

            # Note that the resulting RX graph will have multigraph set to False which
            # ensures that there is never more than one edge between two specific nodes.
            # This is perhaps not all that interesting in general, but it is critical
            # when getting the edge_id from an edge using RX.edge_indices_from_endpoints()
            # routine - because it ensures that only a single edge_id is returned...

            converted_graph = Graph.from_rustworkx(rx_graph)

            # Some graphs have geometry data (from a geodataframe), so preserve it if it exists
            if hasattr(self, "geometry"):
                converted_graph.geometry = self.geometry

            # Create a mapping from the old NX node_ids to the new RX node_ids (created by
            # RX when it converts from NX)
            nx_to_rx_node_id_map = {
              converted_graph.node_data(node_id)["__networkx_node__"]: node_id
              for node_id in converted_graph._rx_graph.node_indices()
            }
            converted_graph.nx_to_rx_node_id_map = nx_to_rx_node_id_map

            # We also have to update the _node_id_to_original_nx_node_id_map to refer to the node_ids
            # in the NX Graph object.
            _node_id_to_original_nx_node_id_map = {}
            for node_id in converted_graph.node_indices:
                original_nx_node_id = converted_graph.node_data(node_id)["__networkx_node__"]
                _node_id_to_original_nx_node_id_map[node_id] = original_nx_node_id
            converted_graph._node_id_to_original_nx_node_id_map = _node_id_to_original_nx_node_id_map

            return converted_graph
        elif self.is_rx_graph():
            return self
        else: 
            raise TypeError(
              "Graph passed to 'convert_from_nx_to_rx()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def get_nx_to_rx_node_id_map(self) -> dict[Any, Any]:
        """
        Return the dict that maps NX node_ids to RX node_ids

        The primary use case for this routine is to support automatically
        converting NX-based graph objects to be RX-based when creating a 
        Partition object.  The issue is that when you convert from NX to RX
        the node_ids change and so you need to update the Partition object's
        Assignment to use the new RX node_ids.  This routine is used
        to translate those NX node_ids to the new RX node_ids when 
        initializing a Partition object.

        :rtype: dict[Any, Any]
        """
        # Simple getter method
        if not self.is_rx_graph():
            raise TypeError(
              "Graph passed to 'get_nx_to_rx_node_id()' is not a rustworkx graph"
            )

        return self.nx_to_rx_node_id_map

    @classmethod
    def from_json(cls, json_file_name: str) -> "Graph":
        """
        Create a :class:`Graph` from a JSON file

        :param json_file_name: JSON file
            # frm: TODO: Documentation: more detail on contents of JSON file needed here
        :type json_file_name: str

        :returns: A GerryChain Graph object with data from JSON file
        :rtype: "Graph"
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
        """
        Dump a GerryChain Graph object to disk as a JSON file

        :param json_file_name: name of JSON file to be created
        :type json_file_name: str

        :rtype: None
        """
        # frm TODO: Code: Implement graph.to_json for an RX based graph
        if not self.is_nx_graph():
            raise TypeError(
              "Graph passed to 'to_json()' is not a networkx graph"
            )

        data = json_graph.adjacency_data(self._nx_graph)

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
        cols_to_add: Optional[list[str]] = None,
        reproject: bool = False,
        ignore_errors: bool = False,
    ) -> "Graph":
        """
        Create a :class:`Graph` from a shapefile (or GeoPackage, or GeoJSON, or
        any other library that :mod:`geopandas` can read. See :meth:`from_geodataframe`
        for more details.

        :param filename: Path to the shapefile / GeoPackage / GeoJSON / etc.
        :type filename: str
        :param adjacency: The adjacency type to use ("rook" or "queen"). Default is "rook"
        :type adjacency: str, optional
        :param cols_to_add: The names of the columns that you want to
            add to the graph as node attributes. Default is None.
        :type cols_to_add: Optional[list[str]], optional
        :param reproject: Whether to reproject to a UTM projection before
            creating the graph. Default is False.
        :type reproject: bool, optional
        :param ignore_errors: Whether to ignore all invalid geometries and try to continue
            creating the graph. Default is False.
        :type ignore_errors: bool, optional

        :returns: The Graph object of the geometries from `filename`.
        :rtype: Graph

        .. Warning::

            This method requires the optional ``geopandas`` dependency.
            So please install ``gerrychain`` with the ``geo`` extra
            via the command:

            .. code-block:: console

                pip install gerrychain[geo]

            or install ``geopandas`` separately.
        """

        df = gp.read_file(filename)
        graph = cls.from_geodataframe(
            df,
            adjacency=adjacency,
            cols_to_add=cols_to_add,
            reproject=reproject,
            ignore_errors=ignore_errors,
        )
        # frm: TODO: Documentation: Make it clear that this creates an NX-based
        #               Graph object.
        #
        #               Also add some documentation (here or elsewhere)
        #               about what CRS data is and what it is used for.
        # 
        #               Note that the NetworkX.Graph.graph["crs"] is only
        #               ever accessed in this file (graph.py), so I am not
        #               clear what it is used for.  It seems to just be set
        #               and never used except to be written back out to JSON.
        #
        #               The issue (I think) is that we do not preserve graph
        #               attributes when we convert to RX from NX, so if the
        #               user wants to write an RX based Graph back out to JSON
        #               this data (and another other graph level data) would be
        #               lost.
        #
        #               So - need to figure out what CRS is used for...
        #
        # Peter commented on this in a PR comment:
        # 
        # CRS stands for "Coordinate Reference System" which can be thought of 
        # as the projection system used for the polygons contained in the 
        # geodataframe. While it is not used in any of the graph operations of 
        # GerryChain, it may be used in things like validators and updaters. Since 
        # the CRS determines the projection system used by the underlying 
        # geodataframe, any area or perimeter computations encoded on the graph 
        # are stored with the understanding that those values may inherit 
        # distortions from projection used. We keep this around as metadata so 
        # that, in the event that the original geodataframe source is lost, 
        # the graph metadata still carries enough information for us to sanity 
        # check the area and perimeter computations if we get weird numbers.


        # Store CRS data as an attribute of the NX graph
        graph._nx_graph.graph["crs"] = df.crs.to_json()
        return graph

    @classmethod
    def from_geodataframe(
        cls,
        dataframe: pd.DataFrame,
        adjacency: str = "rook",
        cols_to_add: Optional[list[str]] = None,
        reproject: bool = False,
        ignore_errors: bool = False,
        crs_override: Optional[Union[str, int]] = None,
    ) -> "Graph":
        
        # frm: Changed to operate on a NetworkX.Graph object and then convert to a
        #       Graph object at the end of the function.

        """
        Create the adjacency :class:`Graph` of geometries described by `dataframe`.
        The areas of the polygons are included as node attributes (with key `area`).
        The shared perimeter of neighboring polygons are included as edge attributes
        (with key `shared_perim`).
        Nodes corresponding to polygons on the boundary of the union of all the geometries
        (e.g., the state, if your dataframe describes VTDs) have a `boundary_node` attribute
        (set to `True`) and a `boundary_perim` attribute with the length of this "exterior"
        boundary.

        By default, areas and lengths are computed in a UTM projection suitable for the
        geometries. This prevents the bizarro area and perimeter values that show up when
        you accidentally do computations in Longitude-Latitude coordinates. If the user
        specifies `reproject=False`, then the areas and lengths will be computed in the
        GeoDataFrame's current coordinate reference system. This option is for users who
        have a preferred CRS they would like to use.

        :param dataframe: The GeoDateFrame to convert
        :type dataframe: :class:`geopandas.GeoDataFrame`
        :param adjacency: The adjacency type to use ("rook" or "queen").
            Default is "rook".
        :type adjacency: str, optional
        :param cols_to_add: The names of the columns that you want to
            add to the graph as node attributes. Default is None.
        :type cols_to_add: Optional[list[str]], optional
        :param reproject: Whether to reproject to a UTM projection before
            creating the graph. Default is ``False``.
        :type reproject: bool, optional
        :param ignore_errors: Whether to ignore all invalid geometries and
            attept to create the graph anyway. Default is ``False``.
        :type ignore_errors: bool, optional
        :param crs_override: Value to override the CRS of the GeoDataFrame.
            Default is None.
        :type crs_override: Optional[Union[str,int]], optional

        :returns: The adjacency graph of the geometries from `dataframe`.
        :rtype: Graph
        """
        # Validate geometries before reprojection
        if not ignore_errors:
            invalid = invalid_geometries(dataframe)
            if len(invalid) > 0:
                raise GeometryError(
                    "Invalid geometries at rows {} before "
                    "reprojection. Consider repairing the affected geometries with "
                    "`.buffer(0)`, or pass `ignore_errors=True` to attempt to create "
                    "the graph anyways.".format(invalid)
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
                        "Invalid geometries at rows {} after "
                        "reprojection. Consider reloading the GeoDataFrame with "
                        "`reproject=False` or repairing the affected geometries "
                        "with `.buffer(0)`.".format(invalid_reproj)
                    )
        else:
            df = dataframe

        # Generate dict of dicts of dicts with shared perimeters according
        # to the requested adjacency rule
        adjacencies = neighbors(df, adjacency)      # Note - this is adjacency.neighbors()

        nx_graph = networkx.Graph(adjacencies)

        # frm: TODO: Documentation:  Document what geometry is used for.
        # 
        #               Need to grok what geometry is used for - it is used in partition.py.plot()
        #               and maybe that is the only place it is used, but it is also used below
        #               to set other data, such as add_boundary_perimeters() and areas.  The
        #               reason this is an issue is because I need to know what to carry over to
        #               the RX version of a Graph when I convert to RX when making a Partition.
        #               Partition.plot() uses this information, so it needs to be available in
        #               the RX version of a Graph - which essentially means that I need to grok
        #               how plot() works and where it gets its information and how existing 
        #               users use it...
        #
        # There is a test failure due to geometry not being available after conversion to RX.
        #
        # Here is what Peter said in the PR:
        #
        # The geometry attribute on df is a special attribute that only appears on 
        # geodataframes. This is just a list of polygons representing some real-life 
        # geometries underneath a certain projection system (CRS). These polygons can 
        # then be fed to matplotilb to make nice plots of things, or they can be used 
        # to compute things like area and perimeter for use in updaters and validators 
        # that employ some sort of Reock score (uncommon, but unfortunately necessary in 
        # some jurisdictions). We probably don't need to store this as an attribute on 
        # the Graph._nxgraph object (or the Graph._rxgraph) object, however. In fact, it 
        # might be best to just make a Graph.dataframe attribute to store all of the 
        # graph data on, and add attributes to _nxgraph and _rxgraph nodes as needed
        # 

        nx_graph.geometry = df.geometry

        # frm: TODO: Refactoring: Rethink the name of add_boundary_perimeters
        # 
        # It acts on an nx_graph which seems wrong with the given name.  
        # Maybe it should be: add_boundary_perimeters_to_nx_graph()
        #
        # Need to check in with Peter to see if this is considered 
        # part of the external API.

        # frm: TODO: Refactoring: Create an nx_utilities module
        #
        # It raises the question of whether there should be an nx_utilities 
        # module for stuff designed to only work on nx_graph objects.
        #
        # Note that Peter said: "I like this idea" 
        #

        # Add "exterior" perimeters to the boundary nodes
        add_boundary_perimeters(nx_graph, df.geometry)

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
    def node_indices(self) -> set[Any]:
        """
        Return a set of the node_ids in the graph

        :rtype: set[Any]
        """
        self.verify_graph_is_valid()

        # frm: TODO: Refactoring:  node_indices() does the same thing that graph.nodes does - returning a list of node_ids.
        #               Do we really want to support two ways of doing the same thing?
        # Actually this returns a set rather than a list - not sure that matters though...
        #
        # My code uses node_indices() to make it clear we are talking about node_ids...
        #
        # The question is whether to deprecate nodes()...

        if (self.is_rx_graph()):
            return set(self._rx_graph.node_indices())
        elif (self.is_nx_graph()):
            return set(self._nx_graph.nodes)
        else:
            raise TypeError(
              "Graph passed to 'node_indices()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    @property
    def edge_indices(self) -> set[Any]:
        """
        Return a set of the edge_ids in the graph

        :rtype: set[Any]
        """
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # A set of edge_ids for the edges
            return set(self._rx_graph.edge_indices())
        elif (self.is_nx_graph()):
            # A set of edge_ids (tuples) extracted from the graph's EdgeView
            return set(self._nx_graph.edges)
        else:
            raise TypeError(
              "Graph passed to 'edge_indices()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def get_edge_from_edge_id(self, edge_id: Any) -> tuple[Any, Any]:
        """
        Return the edge (tuple of node_ids) corresponding to the 
        given edge_id

        Note that in NX, an edge_id is the same as an edge - it is
        just a tuple of node_ids.  However, in RX, an edge_id is
        an integer, so if you want to get the tuple of node_ids
        you need to use the edge_id to get that tuple...

        :param edge_id: The ID of the desired edge
        :type edge_id: Any

        :returns: An edge, namely a tuple of node_ids
        :rtype: tuple[Any, Any]
        """

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # In RX, we need to go get the edge tuple
            # frm: TODO: Performance - use get_edge_endpoints_by_index() to get edge 
            #
            # The original RX code (before October 27, 2025):
            #     return self._rx_graph.edge_list()[edge_id]
            endpoints = self._rx_graph.get_edge_endpoints_by_index(edge_id)
            return (endpoints[0], endpoints[1])
        elif (self.is_nx_graph()):
            # In NX, the edge_id is also the edge tuple
            return edge_id
        else:
            raise TypeError(
              "Graph passed to 'get_edge_from_edge_id()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    # frm: TODO: Refactoring: Create abstract "edge" and "edge_id" type names
    #
    # As with node_id, this is cosmetic but it will provide a nice place to
    # put a comment about the difference between NX and RX and it will make
    # the type annotations make more sense...

    def get_edge_id_from_edge(self, edge: tuple[Any, Any]) -> Any:
        """
        Get the edge_id that corresponds to the given edge.

        In RX an edge_id is an integer that designates an edge (an edge is
        a tuple of node_ids).  In NX, an edge_id IS the tuple of node_ids.
        So, in general, to support both NX and RX, if you want to get access
        to the edge data for an edge (tuple of node_ids), you need to 
        ask for the edge_id.

        This functionality is needed, for instance, when 

        :param edge: A tuple of node_ids.
        :type edge: tuple[Any, Any]

        :returns: The ID associated with the given edge
        :rtype: Any
        """
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):

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
            edge_indices = self._rx_graph.edge_indices_from_endpoints(edge[0], edge[1])
            return edge_indices[0]  # there will always be one and only one 
        elif (self.is_nx_graph()):
            # In NX, the edge_id is also the edge tuple
            return edge
        else:
            raise TypeError(
              "Graph passed to 'get_edge_id_from_edge()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    @property
    def nodes(self) -> list[Any]:
        """
        Return a list of all of the node_ids in the graph.

        This routine still exists because there is a lot of legacy
        code that uses this syntax to iterate through all of the nodes
        in a graph.  

        There is another routine, node_indices(), which does essentially
        the same thing (it returns a set of node_ids, however, rather than 
        a list).

        Why have two routines that do the same thing?  The answer is that with 
        move to RX, it seemed appropriate to emphasize the distinction 
        between objects and the IDs for objects, hence the introduction of
        node_indices() and edge_indices() routines.  This distinction is 
        critical for edges, but mostly not important for nodes.  In fact
        this routine is implemented by just converting node_indices to a list.
        So, it is essentially a style issue - when referring to nodes, we
        are almost always really referring to node_ids, so why not use a
        routine called node_indices()?

        Note that there is a subtle point to be made about node names vs.
        node_ids.  It was common before the transition to RX to create 
        nodes with IDs that were essentially names.  That is, the ID had
        semantic weight.  This is not true with RX node_ids.  So, any
        code that relies on the semantics of a node's ID (treating it 
        like a name) is suspect in the new RX world.

        :returns: A list of all of the node_ids in the graph
        :rtype: list[Any]
        """

        # frm: TODO: Documentation:  Warn users in Migration Guide that nodes() has gone away
        #
        # Since the legacy code implemented a GerryChain Graph as a subclass of NetworkX.Graph
        # legacy code could take advantage of NX cleverness - NX returns a NodeView object for
        # nx_graph.nodes which supports much more than just a list of node_ids (which is all that
        # code below does).
        # 
        # Probably the most common use of nx_graph.nodes was to access node data as in:
        #
        #    nx_graph.nodes[node_id][<dict_key_for_attribute_value>]
        #
        # In the new world, to do that you need to do:
        #
        #    graph.node_data(node_id)[<dict_key_for_attribute_value>]
        #
        # So, almost the same number of keystrokes, but if a legacy user uses nodes[...] the
        # old way, it won't work out well.
        #

        # frm: TODO: Refactoring: Think about whether to do away entirely with graph.nodes
        #
        # All this routine does now is to coerce the set of nodes obtained by node_indices()
        # to be a list (which I think is unnecessary).  So, why have it at all?  Why not just
        # tell legacy users via an exception that it no longer exists?
        #
        # On the other hand, it maybe does no harm to allow legacy users to indulge in 
        # what appears to be a very common idiom in legacy code...

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # A list of integer node_ids
            return list(self._rx_graph.node_indices())
        elif (self.is_nx_graph()):
            # A list of node_ids -  
            return list(self._nx_graph.nodes)
        else:
            raise TypeError(
              "Graph passed to 'nodes()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    @property
    def edges(self) -> set[tuple[Any, Any]]:
        """
        Return a set of all of the edges in the graph, where each 
        edge is a tuple of node_ids

        :rtype: set[tuple[Any, Any]]:
        """
        # Return a set of edge tuples

        # frm: TODO: Code: ???: Should edges return a list instead of a set?
        #
        # Peter said he thought users would expect a list - but why?

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # A set of tuples for the edges
            return set(self._rx_graph.edge_list())
        elif (self.is_nx_graph()):
            # A set of tuples extracted from the graph's EdgeView
            return set(self._nx_graph.edges)
        else:
            raise TypeError(
              "Graph passed to 'edges()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def add_edge(self, node_id1: Any, node_id2: Any) -> None:
        """
        Add an edge to the graph from node_id1 to node_id2

        :param node_id1: The node_id for one of the nodes in the edge
        :type node_id1: Any
        :param node_id2: The node_id for one of the nodes in the edge
        :type node_id2: Any

        :rtype: None
        """

        # frm: TODO: Code: add_edge(): Check that nodes exist and that they have data dicts.
        #
        # This checking should probably be limited to development mode, but
        # the issue is that an RX node need not have a data value that is 
        # a dict, but GerryChain code depends on having a data dict.  So,
        # it makes sense to test and make sure that the nodes exist and 
        # have a data dict...

        # frm: TODO: Code: add_edge(): Do we need to check to make sure the edge does not already exist?

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # empty dict tells RX the edge data will be a dict 
            self._rx_graph.add_edge(node_id1, node_id2, {})
        elif (self.is_nx_graph()):
            self._nx_graph.add_edge(node_id1, node_id2)
        else:
            raise TypeError(
              "Graph passed to 'add_edge()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def add_data(
        self,  df: pd.DataFrame, columns: Optional[Iterable[str]] = None
    ) -> None:
        """
        Add columns of a DataFrame to a graph as node attributes
        by matching the DataFrame's index to node ids.

        :param df: Dataframe containing given columns.
        :type df: :class:`pandas.DataFrame`
        :param columns: list of dataframe column names to add. Default is None.
        :type columns: Optional[Iterable[str]], optional

        :returns: None
        """

        if not (self.is_nx_graph()):
            raise TypeError(
              "Graph passed to 'add_data()' is not a networkx graph"
            )

        if columns is None:
            columns = list(df.columns)

        check_dataframe(df[columns])

        # Create dict: {node_id: {attr_name: attr_value}}
        column_dictionaries = df.to_dict("index")
        nx_graph = self._nx_graph
        networkx.set_node_attributes(nx_graph, column_dictionaries)

        if hasattr(nx_graph, "data"):
            nx_graph.data[columns] = df[columns]  # type: ignore
        else:
            nx_graph.data = df[columns]


    def join(
        self,
        dataframe: pd.DataFrame,
        columns: Optional[list[str]] = None,
        left_index: Optional[str] = None,
        right_index: Optional[str] = None,
    ) -> None:
        """
        Add data from a dataframe to the graph, matching nodes to rows when
        the node's `left_index` attribute equals the row's `right_index` value.

        :param dataframe: DataFrame.
        :type dataframe: :class:`pandas.DataFrame`
        :columns: The columns whose data you wish to add to the graph.
            If not provided, all columns are added. Default is None.
        :type columns: Optional[list[str]], optional
        :left_index: The node attribute used to match nodes to rows.
            If not provided, node IDs are used. Default is None.
        :type left_index: Optional[str], optional
        :right_index: The DataFrame column name to use to match rows
            to nodes. If not provided, the DataFrame's index is used. Default is None.
        :type right_index: Optional[str], optional

        :returns: None
        """
        if right_index is not None:
            df = dataframe.set_index(right_index)
        else:
            df = dataframe

        if columns is not None:
            df = df[columns]

        check_dataframe(df)

        column_dictionaries = df.to_dict()

        # frm: TODO: Code: Implement graph.join() for RX
        #
        # This is low priority given that current suggested coding
        # strategy of creating the graph using NX and then letting
        # GerryChain convert it automatically to RX.  In this scenario
        # any joins would happen to the NX-based graph only.

        if not self.is_nx_graph():
            raise TypeError(
              "Graph passed to join() is not a networkx graph"
            )
        nx_graph = self._nx_graph

        if left_index is not None:
            ids_to_index = networkx.get_node_attributes(nx_graph, left_index)
        else:
            # When the left_index is node ID, the matching is just
            # a redundant {node: node} dictionary
            ids_to_index = dict(zip(self.nodes, self.nodes))

        node_attributes = {
            node_id: {
                column: values[index] for column, values in column_dictionaries.items()
            }
            for node_id, index in ids_to_index.items()
        }

        networkx.set_node_attributes(nx_graph, node_attributes)

    @property
    def islands(self) -> set[Any]:
        """
        Return a set of all node_ids that are not connected via an
        edge to any other node in the graph - that is, nodes with
        degree = 0

        :returns: A set of all node_ids for nodes of degree 0
        :rtype: set[Any]
        """
        # Return all nodes of degree 0 (those not connected in an edge to another node)
        return set(node_id for node_id in self.node_indices if self.degree(node_id) == 0)

    def is_directed(self) -> bool:
        # frm TODO: Code:   Delete this code: graph.is_directed() once convinced it is safe to do so...
        # 
        # I added it because code in contiguity.py 
        # called nx.is_connected() which eventually called is_directed()
        # assuming the graph was an nx_graph.
        #
        # Changing from return False to raising an exception just to make 
        # sure nobody uses it.  

        raise NotImplementedError("graph.is_directed() should not be used")

    
    def warn_for_islands(self) -> None:
        """
        Issue a warning if there are any islands in the graph - that is,
        if there are any nodes in the graph that are not connected to any
        other node (degree = 0)

        :rtype: None
        """
        islands = self.islands
        if len(self.islands) > 0:
            warnings.warn(
                "Found islands (degree-0 nodes). Indices of islands: {}".format(islands)
        )
    
    def issue_warnings(self) -> None:
        """
        Issue any warnings concerning the content or structure
        of the graph.

        :rtype: None
        """
        self.warn_for_islands()

    def __len__(self) -> int:
        """
        Return the number of nodes in the graph

        :rtype: int
        """
        return len(self.node_indices)

    def __getattr__(self, __name: str) -> Any:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        # frm: TODO: Code: Get rid of _getattr_ eventually - it is very dangerous...

        # frm: Interesting bug lurking if __name is "nx_graph".  This occurs when legacy code
        #       uses the default constructor, Graph(), and then references a built-in NX
        #       Graph method, such as my_graph.add_edges().  In this case the built-in NX 
        #       Graph method is not defined, so __getattr__() is called to try to figure out
        #       what it could be.  This triggers the call below to self.is_nx_graph(), which 
        #       references self._nx_graph (which is undefined/None) which triggers another 
        #       call to __getattr__() which is BAD...
        #
        #       I think the solution is to not rely on testing whether nx_graph and rx_graph
        #       are None - but rather to have explicit is_nx_or_rx_graph data member which
        #       is set to one of "NX", "RX", "not_set".
        #
        #       For now, I am just going to return None if __name is "_nx_graph" or "_rx_graph".
        # 
        # Peter's comments from PR:
        #
        # Oh interesting; good catch! The flag approach seems like a good solution to me. 
        # It's very, very rare to use the default constructor, so I don't imagine that 
        # people will really run into this.

        # frm: TODO: Code: Fix this hack (in __getattr__) - see comment above...
        if (__name == "_nx_graph") or (__name == "_rx_graph"):
            return None

        # If attribute doesn't exist on this object, try
        # its underlying graph object...
        if (self.is_rx_graph()):
            return object.__getattribute__(self._rx_graph, __name)
        elif (self.is_nx_graph()):
            return object.__getattribute__(self._nx_graph, __name)
        else:
            raise TypeError(
              "Graph passed to '__gettattr__()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def __getitem__(self, __name: str) -> Any:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        # frm: TODO: Code: Does any of the code actually use __getitem__ ?
        #
        #           It is a clever Python way to use square bracket
        #           notation to access something (anything) you want.
        #
        #           In this case, it returns the NetworkX AtlasView
        #           of neighboring nodes - looks like a dictionary
        #           with a key of the neighbor node_id and a value
        #           with the neighboring node's data (another dict).
        #
        #           I am guessing that it is only ever used to get
        #           a list of the neighbor node_ids, in which case
        #           it is functionally equivalent to self.neighbors().
        #
        #           *sigh*
        #
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # frm TODO: Code: Decide if __getitem__() should work for RX
            raise TypeError("Graph._getitem__() is not defined for a rustworkx graph")
        elif (self.is_nx_graph()):
            return self._nx_graph[__name]
        else:
            raise TypeError(
              "Graph passed to '__getitem__()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def __iter__(self) -> Iterable[Any]:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        yield from self.node_indices

    def subgraph(self, nodes: Iterable[Any]) -> "Graph":
        """
        Create a subgraph that contains the given nodes.

        Note that creating a subgraph of an RustworkX (RX) graph 
        renumbers the nodes, so that a node that had node_id: 4
        in the parent graph might have node_id: 2 in the subgraph.
        This is a HUGE difference from the NX world where the 
        node_ids in a subgraph do not change from those in the 
        parent graph.

        In order to make sense of the nodes in a subgraph in the
        RX world, we need to maintain mappings from the node_ids
        in the subgraph to the node_ids of the immediate parent
        graph and to the "original" top-level graph that contains
        all of the nodes.  You will notice the creation of those
        maps in the code below.

        :param nodes: The nodes to be included in the subgraph
        :type nodes: Iterable[Any]

        :returns: A subgraph containing the given nodes.
        :rtype: "Graph"
        """

        """
        frm: RX Documentation:

        Subgraphs are one of the biggest differences between NX and RX, because RX creates new
        node_ids for the nodes in the subgraph, starting at 0.  So, if you create a subgraph with
        a list of nodes: [45, 46, 47] the nodes in the subgraph will be [0, 1, 2].

        This creates problems for functions that operate on subgraphs and want to return results
        involving node_ids to the caller.  To solve this, we define a _node_id_to_parent_node_id_map whenever
        we create a subgraph that will provide the node_id in the parent for each node in the subgraph.
        For NX this is a no-op, and the _node_id_to_parent_node_id_map is just an identity map - each node_id is 
        mapped to itself.  For RX, however, we store the parent_node_id in the node's data before
        creating the subgraph, and then in the subgraph, we use the parent's node_id to construct 
        a map from the subgraph node_id to the parent_node_id.

        This means that any function that wants to return results involving node_ids can safely
        just translate node_ids using the _node_id_to_parent_node_id_map, so that the results make sense in
        the caller's context.

        A note of caution: if the caller retains the subgraph after using it in a function call, 
        the caller should almost certainly not use the node_ids in the subgraph for ANYTHING.
        It would be safest to reset the value of the subgraph to None after using it as an
        argument to a function call.

        Also, for both RX and NX, we set the _node_id_to_parent_node_id_map to be the identity map for top-level
        graphs on the off chance that there is a function that takes both top-level graphs and 
        subgraphs as a parameter.  This allows the function to just always do the node translation.
        In the case of a top-level graph the translation will be a no-op, but it will be correct.

        Also, we set the _is_a_subgraph = True, so that we can detect whether a parameter passed into
        a function is a top-level graph or not.  This will allow us to debug the code to determine 
        if assumptions about a parameter always being a subgraph is accurate.  It also helps to 
        educate future readers of the code that subgraphs are "interesting"...

        """

        self.verify_graph_is_valid()

        new_subgraph = None

        if (self.is_nx_graph()):
            nx_subgraph = self._nx_graph.subgraph(nodes)
            new_subgraph = self.from_networkx(nx_subgraph)
            # for NX, the node_ids in subgraph are the same as in the parent graph
            _node_id_to_parent_node_id_map = {node: node for node in nodes}
            _node_id_to_original_nx_node_id_map = {node: node for node in nodes}   
        elif (self.is_rx_graph()):
            if isinstance(nodes, frozenset) or isinstance(nodes, set):
                nodes = list(nodes)

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
                if not ("__networkx_node__" in self.node_data(node_id)):
                    raise Exception("subgraph: internal error: original_nx_node_id not set")

            rx_subgraph = self._rx_graph.subgraph(nodes)
            new_subgraph = self.from_rustworkx(rx_subgraph)

            # frm: Create the map from subgraph node_id to parent graph node_id
            _node_id_to_parent_node_id_map = {}
            for subgraph_node_id in new_subgraph.node_indices:
                _node_id_to_parent_node_id_map[subgraph_node_id] = \
                  new_subgraph.node_data(subgraph_node_id)["parent_node_id"]
                # value no longer needed, so delete it
                new_subgraph.node_data(subgraph_node_id).pop("parent_node_id") 

            # frm: Create the map from subgraph node_id to the original graph's node_id
            _node_id_to_original_nx_node_id_map = {}
            for subgraph_node_id in new_subgraph.node_indices:
                _node_id_to_original_nx_node_id_map[subgraph_node_id] = \
                  new_subgraph.node_data(subgraph_node_id)["__networkx_node__"]
        else:
            raise TypeError(
              "Graph passed to 'subgraph()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

        new_subgraph._is_a_subgraph = True
        new_subgraph._node_id_to_parent_node_id_map = _node_id_to_parent_node_id_map
        new_subgraph._node_id_to_original_nx_node_id_map = _node_id_to_original_nx_node_id_map

        return new_subgraph

    # frm: TODO: Refactoring: Create abstract type name for "Flip" and "Flip_Dict".  
    #
    # This is cosmetic, but it would (IMHO) make the code easier to understand, and it
    # would provide a logical place to define WTF a flip is...

    def translate_subgraph_node_ids_for_flips(self, flips: dict[Any, int]) -> dict[Any, int]:
        """
        Translate the given flips so that the subgraph node_ids in the flips
        have been translated to the appropriate node_ids in the 
        parent graph.

        The flips parameter is a dict mapping node_ids to parts (districts).

        This routine is used when a computation that creates flips is made 
        on a subgraph, but those flips want to be translated into the context
        of the parent graph at the end of the computation.

        For more details, refer to the larger comment on subgraphs...

        :param flips: A dict containing "flips" which associate a node with
            a new part in a partition (a "part" is the same as a district in 
            common parlance).
        :type flips: dict[Any, int]

        :returns: A dict containing "flips" that have been translated to have
            node_ids appropriate for the parent graph
        :rtype: dict[Any, int]
        """

        # frm: TODO: Documentation: Write an overall comment on subgraphs and node_id maps

        translated_flips = {}
        for subgraph_node_id, part in flips.items():
            parent_node_id = self._node_id_to_parent_node_id_map[subgraph_node_id]
            translated_flips[parent_node_id] = part

        return translated_flips

    def translate_subgraph_node_ids_for_set_of_nodes(self, set_of_nodes: set[Any]) -> set[Any]:
        """
        Translate the given set_of_nodes to have the appropriate
        node_ids for the parent graph.

        This routine is used when a computation that creates a set of nodes is made 
        on a subgraph, but those nodes want to be translated into the context
        of the parent graph at the end of the computation.

        For more details, refer to the larger comment on subgraphs...

        :param set_of_nodes: A set of node_ids in a subgraph
        :type set_of_nodes: set[Any]

        :returns: A set of node_ids that have been translated to have 
            the node_ids appropriate for the parent graph
        :rtype: set[Any]
        """
        # This routine replaces the node_ids of the subgraph with the node_ids
        # for the same node in the parent graph.  This routine is used to
        # when a computation is made on a subgraph but the resulting set of nodes
        # being returned want to be the appropriate node_ids for the parent graph.
        translated_set_of_nodes = set()
        for node_id in set_of_nodes:
            translated_set_of_nodes.add(self._node_id_to_parent_node_id_map[node_id])
        return translated_set_of_nodes

    def generic_bfs_edges(self, source, neighbors=None, depth_limit=None) -> Generator[tuple[Any, Any], None, None]:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        # frm: Code copied from GitHub:
        #
        #  https://github.com/networkx/networkx/blob/main/networkx/algorithms/traversal/breadth_first_search.py
        #
        #       Code was not modified - it worked as written for both rx.PyGraph and a graph.Graph object
        #       with an RX graph embedded in it...
        
        """Iterate over edges in a breadth-first search.

        The breadth-first search begins at `source` and enqueues the
        neighbors of newly visited nodes specified by the `neighbors`
        function.

        Parameters
        ----------
        G : RustworkX.PyGraph object (not a NetworkX graph)

        source : node
            Starting node for the breadth-first search; this function
            iterates over only those edges in the component reachable from
            this node.

        neighbors : function
            A function that takes a newly visited node of the graph as input
            and returns an *iterator* (not just a list) of nodes that are
            neighbors of that node with custom ordering. If not specified, this is
            just the ``G.neighbors`` method, but in general it can be any function
            that returns an iterator over some or all of the neighbors of a
            given node, in any order.

        depth_limit : int, optional(default=len(G))
            Specify the maximum search depth.

        Yields
        ------
        edge
            Edges in the breadth-first search starting from `source`.

        Examples
        --------
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

        Notes
        -----
        This implementation is from `PADS`_, which was in the public domain
        when it was first accessed in July, 2004.  The modifications
        to allow depth limits are based on the Wikipedia article
        "`Depth-limited-search`_".

        .. _PADS: http://www.ics.uci.edu/~eppstein/PADS/BFS.py
        .. _Depth-limited-search: https://en.wikipedia.org/wiki/Depth-limited_search
        """
        # frm: These two if-stmts work for both rx.PyGraph and gerrychain.Graph with RX inside
        if neighbors is None:
            neighbors = self.neighbors
        if depth_limit is None:
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

    # frm: TODO: Testing:  Add tests for all of the new routines I have added...

    def generic_bfs_successors_generator(self, root_node_id: Any) -> Generator[tuple[Any, Any], None, None]:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        # frm: Generate in sequence a tuple for the parent (node_id) and
        #       the children of that node (list of node_ids).
        parent = root_node_id
        children = []
        for p, c in self.generic_bfs_edges(root_node_id):
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
    
    def generic_bfs_successors(self, root_node_id: Any) -> dict[Any: Any]:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        return dict(self.generic_bfs_successors_generator(root_node_id))

    def generic_bfs_predecessors(self, root_node_id: Any) -> dict[Any, Any]:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        # frm Note:  We had do implement our own, because the built-in RX version only worked 
        #               for directed graphs.
        predecessors = []
        for s, t in self.generic_bfs_edges(root_node_id):
            predecessors.append((t,s))
        return dict(predecessors)


    def predecessors(self, root_node_id: Any) -> dict[Any: Any]:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
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

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            return self.generic_bfs_predecessors(root_node_id)
        elif (self.is_nx_graph()):
            return {a: b for a, b in networkx.bfs_predecessors(self._nx_graph, root_node_id)}
        else:
            raise TypeError(
              "Graph passed to 'predecessors()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def successors(self, root_node_id: Any) -> dict[Any: Any]:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            return self.generic_bfs_successors(root_node_id)
        elif (self.is_nx_graph()):
            return {a: b for a, b in networkx.bfs_successors(self._nx_graph, root_node_id)}
        else:
            raise TypeError(
              "Graph passed to 'successors()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def neighbors(self, node_id: Any) -> list[Any]:
        """
        Return a list of the node_ids of the nodes that are neighbors of 
        the given node - that is, all of the nodes that are directly 
        connected to the given node by an edge.

        :param node_id: The ID of a node
        :type node_id: Any

        :returns: A list of neighbor node_ids
        :rtype: list[Any]
        """
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            return list(self._rx_graph.neighbors(node_id))
        elif (self.is_nx_graph()):
            return list(self._nx_graph.neighbors(node_id))
        else:
            raise TypeError(
              "Graph passed to 'neighbors()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def degree(self, node_id: Any) -> int:
        """
        Return the degree of the given node, that is, the number
        of other nodes directly connected to the given node.

        :param node_id: The ID of a node
        :type node_id: Any

        :returns: Number of nodes directly connected to the given node
        :rtype: int
        """
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            return self._rx_graph.degree(node_id)
        elif (self.is_nx_graph()):
            return self._nx_graph.degree(node_id)
        else:
            raise TypeError(
              "Graph passed to 'degree()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

    def node_data(self, node_id: Any) -> dict[Any, Any]:
        """
        Return the data dictionary that contains the given node's data.

        As docmented elsewhere, in GerryChain code before the conversion
        to RustworkX, users could access node data using the syntax:

            graph.nodes[node_id][attribute_name]
        
        This was because a GerryChain Graph object in that codebase was a 
        subclass of NetworkX.Graph, and NetworkX was clever and implemented
        dict-like behavior for the syntax graph.nodes[]...

        This Python cleverness was not carried over to the RustworkX 
        implementation, so in the current GerryChain Graph implementation 
        users need to access node data using the syntax:

            graph.node_data(node_id)[attribute_name]

        :param node_id: The ID of a node
        :type node_id: Any

        :returns: Data dictionary containing the given node's data.
        :rtype: dict[Any, Any]
        """

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            data_dict = self._rx_graph[node_id]
        elif (self.is_nx_graph()):
            data_dict = self._nx_graph.nodes[node_id]
        else:
            raise TypeError(
              "Graph passed to 'node_data()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

        if not isinstance(data_dict, dict):
            raise TypeError("graph.node_data(): data for node is not a dict")
        
        return data_dict

    def edge_data(self, edge_id: Any) -> dict[Any, Any]:
        """
        Return the data dictionary that contains the data for the given edge.

        Note that in NetworkX an edge_id can be almost anything, for instance,
        a string or even a tuple.  However, in RustworkX, an edge_id is 
        an integer.  This code handles both kinds of edge_ids - hence the
        type, Any.

        :param edge_id: The ID of the edge
        :type edge_id: Any

        :returns: The data dictionary for the given edge's data
        :rtype: dict[Any, Any]
        """

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            data_dict = self._rx_graph.get_edge_data_by_index(edge_id)
        elif (self.is_nx_graph()):
            data_dict = self._nx_graph.edges[edge_id]
        else:
            raise TypeError(
              "Graph passed to 'edge_data()' is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

        # Sanity check - RX edges do not need to have a data dict for node data
        #
        # A GerryChain Graph object should always be constructed with a data dict
        # for edge data, but it doesn't hurt to check.
        if not isinstance(data_dict, dict):
            raise TypeError("graph.edge(): data for edge is not a dict")
        
        return data_dict


    # frm: TODO: Documentation: Note:  I added the laplacian_matrix routines as methods of the Graph
    #               class because they are only ever used on Graph objects.  It
    #               bloats the Graph class, but it still seems like the best
    #               option.
    #
    # A goal is to encapsulate ALL NX dependencies in this file.

    def laplacian_matrix(self) -> scipy.sparse.csr_array:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        # A local "gc" (as in GerryChain) version of the laplacian matrix

        # frm: TODO: Code: laplacian_matrix(): should NX and RX return same type (float vs. int)?
        # 
        #               The NX version returns a matrix of integer values while the
        #               RX version returns a matrix of floating point values.  I 
        #               think the reason is that the RX.adjacency_matrix() call
        #               returns an array of floats.
        #
        #               Since the laplacian matrix is used for further numeric
        #               processing, I don't think this matters, but I should 
        #               check to be 100% certain.

        if self.is_rx_graph():
            rx_graph = self._rx_graph
            # 1. Get the adjacency matrix
            adj_matrix = rustworkx.adjacency_matrix(rx_graph)
            # 2. Calculate the degree matrix (simplified for this example)
            degree_matrix = numpy.diag([rx_graph.degree(node) for node in rx_graph.node_indices()])
            # 3. Calculate the Laplacian matrix
            np_laplacian_matrix = degree_matrix - adj_matrix
            # 4.  Convert the NumPy array to a scipy.sparse array
            laplacian_matrix = scipy.sparse.csr_array(np_laplacian_matrix)
        elif self.is_nx_graph():
            nx_graph = self._nx_graph
            laplacian_matrix = networkx.laplacian_matrix(nx_graph)
        else:
            raise TypeError(
              "Graph passed into laplacian_matrix() is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

        return laplacian_matrix

    def normalized_laplacian_matrix(self) -> scipy.sparse.dia_array:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """

        def create_scipy_sparse_array_from_rx_graph(rx_graph: rustworkx.PyGraph) -> scipy.sparse.coo_matrix:
            """
            <Overview text for what the function does>

            :param <param_name>: ...text...
                ...more text...
            :type <param_name>: <type>

            :returns: ...text...
            :rtype: <type>
        """
            num_nodes = rx_graph.num_nodes()

            rows = []
            cols = []
            data = []

            for u, v in rx_graph.edge_list():
                rows.append(u)
                cols.append(v)
                data.append(1)   # simple adjacency matrix, so just 1 not weight attribute

            sparse_array = scipy.sparse.coo_matrix((data, (rows,cols)), shape=(num_nodes, num_nodes))

            return sparse_array

        if self.is_rx_graph():
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

            # frm: TODO:  Get someone to validate that this in fact does the right thing.
            #
            # The one test, test_proposal_returns_a_partition[spectral_recom], in test_proposals.py
            # that uses normalized_laplacian_matrix() now passes, but it is for a small 6x6 graph
            # and hence is not a real world test...
            #

            A = create_scipy_sparse_array_from_rx_graph(rx_graph)
            n, _ = A.shape          # shape() => dimensions of the array (rows, cols), so n = num_rows
            diags = A.sum(axis=1)   # sum of values in each row => column vector
            diags = diags.T         # convert to a row vector / 1D array
            D = scipy.sparse.dia_array((diags, [0]), shape=(n, n)).tocsr()
            L = D - A
            with numpy.errstate(divide="ignore"):
                diags_sqrt = 1.0 / numpy.sqrt(diags)
            diags_sqrt[numpy.isinf(diags_sqrt)] = 0
            DH = scipy.sparse.dia_array((diags_sqrt, 0), shape=(n, n)).tocsr()
            normalized_laplacian = DH @ (L @ DH)
            return normalized_laplacian

        elif self.is_nx_graph():
            nx_graph = self._nx_graph
            laplacian_matrix = networkx.normalized_laplacian_matrix(nx_graph)
        else:
            raise TypeError(
              "Graph passed into normalized_laplacian_matrix() is neither "
              "a networkx-based graph nor a rustworkx-based graph"
            )

        return laplacian_matrix

    def subgraphs_for_connected_components(self) -> list["Graph"]:
        """
        Create and return a list of subgraphs for each set of nodes
        in the given graph that are connected.

        Note that a connected graph is one in which there is a path
        from every node in the graph to every other node in the 
        graph.
        
        Note also that each of the subgraphs returned is a 
        maximal subgraph of connected components, meaning that there
        is no other larger subgraph of connected components that 
        includes it as a subset.

        :returns: A list of "maximal" subgraphs each of which 
            contains nodes that are connected.
        :rtype: list["Graph"]
        """

        if self.is_rx_graph():
            rx_graph = self.get_rx_graph()
            subgraphs = [
                self.subgraph(nodes) for nodes in rustworkx.connected_components(rx_graph)
            ]
        elif self.is_nx_graph():
            nx_graph = self.get_nx_graph()
            subgraphs = [
              self.subgraph(nodes) for nodes in networkx.connected_components(nx_graph)
            ]
        else:
            raise TypeError(
              "Graph passed to 'subgraphs_for_connected_components()' is "
              "neither a networkx-based graph nor a rustworkx-based graph"
            )
        
        return subgraphs

    def num_connected_components(self) -> int:
        """
        Return the number of connected components.  

        Note: A connected component is a maximal subgraph 
        where every vertex is reachable from every other vertex in 
        that same subgraph. In a graph that is not fully connected, 
        connected components are the separate, distinct "islands" of 
        connected nodes. Every node in a graph belongs to exactly 
        one connected component. 

        :returns: The number of connected components
        :rtype: int
        """

        # frm: TODO: Performance:  num_connected_components(): do both NX and RX have builtins for this?
        #
        # NetworkX and RustworkX both have a routine number_connected_components().  
        # I am guessing that it is more efficient to call these than it is
        # to construct the connected components and then determine how many
        # of them there are.
        #
        # So - should be a simple issue of trying it and running tests, but
        # I will do that another day...
        
        if self.is_rx_graph():
            rx_graph = self.get_rx_graph()
            connected_components = rustworkx.connected_components(rx_graph)
        elif self.is_nx_graph():
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
        """
        Return whether the current graph is a tree - meaning that
        it is connected and that it has no cycles.

        :returns: Whether the current graph is a tree
        :rtype: bool
        """

        # frm: TODO: Refactor: is_a_tree() is only called in a test (test_tree.py) - delete it?
        #
        # Talk to Peter to see if there is any reason to keep this function.  Does anyone
        # use it externally?
        #
        # On the other hand, perhaps it is OK to keep it even if it is only ever used in a test...

        if self.is_rx_graph():
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
        elif self.is_nx_graph():
            nx_graph = self.get_nx_graph()
            return networkx.is_tree(nx_graph)
        else:
            raise TypeError(
              "Graph passed to 'is_a_tree()' is neither a "
              "networkx-based graph nor a rustworkx-based graph"
            )


def add_boundary_perimeters(nx_graph: networkx.Graph, geometries: pd.Series) -> None:
    """
    Add shared perimeter between nodes and the total geometry boundary.

    :param graph: NetworkX graph
    :type graph: :class:`Graph`
    :param geometries: :class:`geopandas.GeoSeries` containing geometry information.
    :type geometries: :class:`pandas.Series`

    :returns: The updated graph.
    :rtype: Graph
    """

    # frm: TODO: add_boundary_perimeters(): Think about whether it is reasonable to require this to work
    #               on an NetworkX.Graph object.

    # frm: The original code operated on the Graph object which was a subclass of
    #       NetworkX.Graph.  I have changed it to operate on a NetworkX.Graph object
    #       with the understanding that callers will reach down into a Graph object
    #       and pass in the inner nx_graph data member.

    if not(isinstance(nx_graph, networkx.Graph)):
        raise TypeError(
          "Graph passed into add_boundary_perimeters() "
          "is not a networkx graph"
        )

    prepared_boundary = prep(unary_union(geometries).boundary)

    boundary_nodes = geometries.boundary.apply(prepared_boundary.intersects)

    for node in nx_graph:
        nx_graph.nodes[node]["boundary_node"] = bool(boundary_nodes[node])
        if boundary_nodes[node]:
            total_perimeter = geometries[node].boundary.length
            shared_perimeter = sum(
                neighbor_data["shared_perim"] for neighbor_data in nx_graph[node].values()
            )
            boundary_perimeter = total_perimeter - shared_perimeter
            nx_graph.nodes[node]["boundary_perim"] = boundary_perimeter

def check_dataframe(df: pd.DataFrame) -> None:
    """
    :returns: None

    :raises: UserWarning if the dataframe has any NA values.
    """
    for column in df.columns:
        if sum(df[column].isna()) > 0:
            warnings.warn("NA values found in column {}!".format(column))


def remove_geometries(data: networkx.Graph) -> None:
    """
    Remove geometry attributes from NetworkX adjacency data object,
    because they are not serializable. Mutates the ``data`` object.

    Does nothing if no geometry attributes are found.

    :param data: an adjacency data object (returned by
        :func:`networkx.readwrite.json_graph.adjacency_data`)
    :type data: networkx.Graph

    :returns: None
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


def convert_geometries_to_geojson(data: networkx.Graph) -> None:
    """
    Convert geometry attributes in a NetworkX adjacency data object
    to GeoJSON, so that they can be serialized. Mutates the ``data`` object.

    Does nothing if no geometry attributes are found.

    :param data: an adjacency data object (returned by
        :func:`networkx.readwrite.json_graph.adjacency_data`)
    :type data: networkx.Graph

    :returns: None
    """
    for node in data["nodes"]:
        for key in node:
            # having a ``__geo_interface__``` property identifies the object
            # as being a ``shapely`` geometry object
            if hasattr(node[key], "__geo_interface__"):
                # The ``__geo_interface__`` property is essentially GeoJSON.
                # This is what :func:`geopandas.GeoSeries.to_json` uses under
                # the hood.
                node[key] = node[key].__geo_interface__


class FrozenGraph:
    """
    Represents an immutable graph to be partitioned. It is based off :class:`Graph`.

    This speeds up chain runs and prevents having to deal with cache invalidation issues.
    This class behaves slightly differently than :class:`Graph` or :class:`networkx.Graph`.

    Not intended to be a part of the public API.

    :ivar graph: The underlying graph.
    :type graph: Graph
    :ivar size: The number of nodes in the graph.
    :type size: int

    Note
    ----
    The class uses `__slots__` for improved memory efficiency.
    """

    # frm: TODO: Code: Rename the internal data member, "graph", to be something else.
    #               The reason is that a NetworkX.Graph object already has an internal
    #               data member named, "graph", which is just a dict for the data
    #               associated with the Networkx.Graph object.
    #
    #               So to avoid confusion, naming the frozen graph something like
    #               _frozen_graph would make it easier for a future reader of the
    #               code to avoid confusion...

    __slots__ = ["graph", "size"]

    def __init__(self, graph: Graph) -> None:
        """
        Initialize a FrozenGraph from a Graph.

        :param graph: The mutable Graph to be converted into an immutable graph
        :type graph: Graph

        :returns: None
        """

        # frm: Original code follows:
        #
        #   self.graph = networkx.classes.function.freeze(graph)
        #   
        #   # frm: frozen is just a function that raises an exception if called...
        #   self.graph.join = frozen
        #   self.graph.add_data = frozen
        #   
        #   self.size = len(self.graph)

        # frm TODO: Code: Add logic to FrozenGraph so that it is indeed "frozen" (for both NX and RX)
        #
        # I think this just means redefining those methods that change the graph
        # to return an error / exception if called.

        self.graph = graph
        self.size = len(self.graph.node_indices)

    def __len__(self) -> int:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        return self.size

    def __getattribute__(self, __name: str) -> Any:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        try:
            return object.__getattribute__(self, __name)
        except AttributeError:
            # delegate getting the attribute to the graph data member
            return self.graph.__getattribute__(__name)

    def __getitem__(self, __name: str) -> Any:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        return self.graph[__name]

    def __iter__(self) -> Iterable[Any]:
        """
        <Overview text for what the function does>

        :param <param_name>: ...text...
            ...more text...
        :type <param_name>: <type>

        :returns: ...text...
        :rtype: <type>
        """
        yield from self.node_indices

    @functools.lru_cache(16384)
    def neighbors(self, n: Any) -> tuple[Any, ...]:
        return self.graph.neighbors(n)

    @functools.cached_property
    def node_indices(self) -> Iterable[Any]:
        return self.graph.node_indices

    @functools.cached_property
    def edge_indices(self) -> Iterable[Any]:
        return self.graph.edge_indices

    @functools.lru_cache(16384)
    def degree(self, n: Any) -> int:
        return self.graph.degree(n)

    def subgraph(self, nodes: Iterable[Any]) -> "FrozenGraph":
        return FrozenGraph(self.graph.subgraph(nodes))
