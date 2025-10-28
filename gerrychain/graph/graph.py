"""
This module provides tools for working with graphs in the context of geographic data.
It extends the functionality of the NetworkX library, adding support for spatial data structures,
geographic projections, and serialization to and from JSON format.

This module is designed to be used in conjunction with geopandas, shapely, and pandas libraries,
facilitating the integration of graph-based algorithms with geographic information systems (GIS).

Note:
This module relies on NetworkX, pandas, and geopandas, which should be installed and
imported as required.
"""

import functools
import json
from typing import Any
import warnings

import networkx
from networkx.classes.function import frozen
from networkx.readwrite import json_graph
import pandas as pd

# frm: added to support RustworkX graphs (in the future)
import rustworkx

from .adjacency import neighbors
from .geo import GeometryError, invalid_geometries, reprojected
from typing import List, Iterable, Optional, Set, Tuple, Union

import geopandas as gp
from shapely.ops import unary_union
from shapely.prepared import prep

import numpy 
import scipy

#########################################################
# frm Overview of changes (May 2025):
# frm: TODO:  Revise (or perhaps just delete) this comment / discussion...
"""
This comment is temporary - it describes the work done to encapsulate dependency on
NetworkX so that this file is the only file that has any NetworkX dependencies.  
That work is not completely done - there are bits and bobs of NetworkX 
dependencies outside this file, but they are at least commented.  In short,
this comment attempts to make clear what I am trying to do.

The idea is to replace the old Graph object (that was a subclass of NetworkX.Graph) with
a new Graph object that is not a subclass of anything.  This new Graph class would look
and act like the old NetworkX based Graph object.  Under the covers it would have 
either an NX Graph or an RX PyGraph.

There is a legitimate question - why bother to retain the option to use a NetworkX Graph
as the underlying Graph object, if the user cannot know what the underlying graph object 
is?  There are two answers:
    1) It seemed possible to me that users took advantage in their own code that the
       Graph object was in fact a NetworkX Graph object.  If that is so, then we can
       make life easier for them by providing them an easy way to gain access to the
       internal NetworkX Graph object so they can continue to use that code.
    2) It was a convenient way to evolve the code - I could make changes, but still
       have some old NX code that I could use as short-term hacks.  It allowed me to
       use a regression test to make sure that it all still ran - some of it running
       with the new Graph object and some of it hacked to operate on the underlying 
       NX Graph data member.

In the future, if #1 is not an issue, we can just expunge NetworkX completely.

I noticed that the FrozenGraph class had already implemented the behavior of the Graph
class but without being a subclass of the NetworkX Graph object.  So, my new Graph class
was based in large part on the FrozenGraph code.  It helped me grok property decorators 
and __getattr__ and __getattribute__ - interesting Pythonic stuff!

It is not the case that ALL of the behavior of the NX based Graph class is replicated
in the new Graph class - I have not implemented NodeView and EdgeView functionality 
and maybe I will not have to.

Note that one of the biggest differences between NetworkX and RustworkX is in how nodes
and edges are identified.  In NetworkX there is not really a difference between the "index"
of a node or an edge and its "name" or "ID" or "value".  In NetworkX the way you index into nodes 
and edges is by using the node's name/Id or the edge's tuple - in effect the index and the 
name/ID/value are the same.  However, in RustworkX, the index is always an integer, and furthermore
the set of indexes for both nodes and edges stats at zero with consecutive integer values.  This
is one of the things that allows RustworkX to be faster than NetworkX.  Converting to using 
RustworkX, therefore, required that the code distinguish between a node/edge's index and its value/ID/name.
This is most visible in the use of node_data() and edge_data() functions and 
in the changes made to the use of subgraphs (which unfortunately have different index values for nodes than
the parent graph in RX).

A note on subgraphs:  Creating subgraphs is a fundamental operation for GerryChain.  When using NX,
a subgraph's node (and also edge) indexes were unchanged from the parent's, so it was safe to do 
calculations on a subgraph and pass back node information (like flips).  However, when using RX, the
node and edge indexes change, so in order to pass back information in the parent's index systems, 
the subgraph's nodes and edges need to be translated back into those of the parent's index system.
In order to do this, every graph contains two new bits of information 1) whether it is a subgraph and
2) a mapping from the subgraph index values to those of its parent.  For top-level (non subgraphs), this
mapping is just an identity mapping - this is just a convenience so that routines can always use the
map without having to worry about whether it is a subgraph or not.

The current state of affairs (early May 2025) is that the code in tree.py has mostly
been converted to use the new Graph object instead of nx.Graph, and that the regression
test works (which only tests some of the functionality, but it does run a chain...)

I have left the original code for the old Graph object in the file so that I could test
that the original and the new code behave the same way - see tests/frm_tests/test_frm_old_vs_new_graph.py
These frm_tests are not yet configured to run as pytest tests, but they soon will be.
I will add additional tests here over time.

Most of the NetworkX dependencies that remain are on NX algorithms (like is_connected() and 
laplacian_matrix()).  These need to be replaced with functions that work on RustworkX Graphs.
I have not yet determined whether they all need to work on both NX and RX graphs - if they
only ever need to work on graphs inside Paritions, then they only need to work for RX, but 
it may be convenient to have them work both ways - needs some thought, and it might be easier 
to just provide compatibility to cover any edge case that I can't think of...

After getting rid of all NX dependencies outside this file, it will be time to switch to
RX which will involve:

    1) Creating RX versions of NX functionality - such as laplacian_matrix().  There are 
       lots of comments in the code saying:  # frm TODO: RX version NYI...     

    2) Adding code so that when we "freeze" a graph, we also convert it to RX.

"""
#########################################################

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
    frm TODO:  Clean up this documentation

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

    # frm: TODO:  Update the comment below - making sure it is 100% accurate (and useful)
    # frm:      This class cannot have a constructor - because there is code that assumes
    #           that it can use the default constructor to create instances of it.
    #           That code is buried deep in non GerryChain code, so I don't really understand
    #           what it is doing, but the assignment of nx_graph and rx_graph class attributes/members
    #           needs to happen in the "from_xxx()" routines.
    #
    # def __init__(self, nx_graph: networkx.Graph, rx_graph: rustworkx.PyGraph)  -> None:
    #     # frm TODO:  check that exactly one param is not None - need one and only one graph...
    #     self._nx_graph = nx_graph
    #     self._rx_graph = rx_graph

    # frm: TODO:    Add documentation for new data members I am adding:
    #               _nx_graph, _rx_graph, _node_id_to_parent_node_id_map, _is_a_subgraph
    #               _node_id_to_original_nx_node_id_map
    #                   => used to recreate NX graph from an RX graph and also 
    #                      as an aid for testing

    @classmethod
    def from_networkx(cls, nx_graph: networkx.Graph) -> "Graph":
        graph = cls()
        graph._nx_graph = nx_graph
        graph._rx_graph = None
        graph._is_a_subgraph = False        # See comments on RX subgraph issues.
        # Maps node_ids in the graph to the "parent" node_ids in the parent graph.
        # For top-level graphs, this is just an identity map 
        graph._node_id_to_parent_node_id_map = {node: node for node in graph.node_indices}   
        # Maps node_ids in the graph to the "original" node_ids in parent graph.
        # For top-level graphs, this is just an identity map 
        graph._node_id_to_original_nx_node_id_map = {node: node for node in graph.node_indices}   
        graph.nx_to_rx_node_id_map = None   # only set when an NX based graph is converted to be an RX based graph
        return graph
    
    @classmethod
    def from_rustworkx(cls, rx_graph: rustworkx.PyGraph) -> "Graph":
        # This routine is intended to be used to create top level graphs that
        # are 1) not subgraphs and 2) not based on NetworkX Graphs.  Stated
        # differently, subgraphs and RX graphs derived from NetworkX graphs 
        # need to create translation maps for node_ids (either to the parent
        # of a subgraph or the "original" node in a NetworkX Graph), and this
        # routine does neither of those things.

        # frm: TODO:  Think about node data dictionaries - do I need to check for them?
        #
        # While NX graphs always have a node data dictionary, RX graphs do not have to 
        # have any data, and the data does not need to be a data dictionary.  Since 
        # gerrychain code depends on having a data dictionary associated with nodes,
        # it probably makes sense to make sure that the rustworkx graph provided
        # as a parameter does in fact have a data dictionary for every node in the
        # graph...
        #
        # The same applies for edge data...
        #

        graph = cls()   
        graph._rx_graph = rx_graph
        graph._nx_graph = None
        graph._is_a_subgraph = False        # See comments on RX subgraph issues.
        # Maps node_ids in the graph to the "parent" node_ids in the parent graph.
        # For top-level graphs, this is just an identity map 
        graph._node_id_to_parent_node_id_map = {node: node for node in graph.node_indices}   
        # Maps node_ids in the graph to the "original" NX node_ids.  At this point, we
        # don't know if this RX based graph was indeed based on an NX graph, so we just 
        # set this to the identity map - which makes sense if this was not derived from
        # and NX-based Graph.  However, in the case when the graph is indeed derived from
        # an NX-based Graph, it is the responsibility of the caller to set 
        # the _node_id_to_original_nx_node_id_map appropriately.
        graph._node_id_to_original_nx_node_id_map = {node: node for node in graph.node_indices}   
        graph.nx_to_rx_node_id_map = None   # only set when an NX based graph is converted to be an RX based graph
        return graph

    def to_networkx_graph(self):
        if self.is_nx_graph():
            return self.get_nx_graph()
        
        if not self.is_rx_graph():
            # frm: TODO: Raise specific exception - type error?
            raise Exception("to_networkx: bad Graph type")

        # OK - we have an RX-based Graph, so create a NetworkX Graph object
        # that has all of the node data and edge data, and which has the
        # original node_ids and edge_ids.
        #
        # Original node_ids are those that were used in the original NX
        # Graph used to create the RX-based Graph object.
        #

        # Confirm that this RX based graph was derived from an NX graph...
        if self._node_id_to_original_nx_node_id_map == None:
            raise Exception("to_networkx_graph: _node_id_to_original_nx_node_id_map is None")

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
        # frm: TODO:  WTF is going on with the line immediately below?
        node_data_dict = nodes_df.to_dict(orient='index')
        networkx.set_node_attributes(nx_graph, nodes_df.to_dict(orient='index'))

        return nx_graph

    # frm: TODO: Create a test for this routine
    def original_nx_node_ids_for_set(self, set_of_nodes):
        # Utility routine to quickly translate a set of node_ids to their original node_ids
        _node_id_to_original_nx_node_id_map = self._node_id_to_original_nx_node_id_map 
        new_set = {_node_id_to_original_nx_node_id_map[node_id] for node_id in set_of_nodes}
        return new_set

    # frm: TODO: Create a test for this routine
    def original_nx_node_ids_for_list(self, list_of_nodes):
        # Utility routine to quickly translate a set of node_ids to their original node_ids
        _node_id_to_original_nx_node_id_map = self._node_id_to_original_nx_node_id_map 
        new_list = [_node_id_to_original_nx_node_id_map[node_id] for node_id in list_of_nodes]
        return new_list
    
    def original_nx_node_id_for_internal_node_id(self, internal_node_id):
        return self._node_id_to_original_nx_node_id_map[internal_node_id]

    # frm: TODO: Create a test for this routine
    def internal_node_id_for_original_nx_node_id(self, original_nx_node_id):
        # frm: TODO:  Think about a better way to map original_nx_node_ids to internal node_ids
        #
        # The problem is that when this routine is called, it may often be called repeatedly 
        # for a list of nodes, and we create the reverse dict every time this is called which
        # is needlessly expensive.  We could just cache this reverse map, but that is often
        # dangerous because we have two sources of truth and if someone needs to update one
        # they may forget to update the other...
        
        # reverse the map so we can go from original node_id to internal node_id
        orignal_node_id_to_internal_node_id_map = {
          v: k for k,v in self._node_id_to_original_nx_node_id_map.items()
        }
        return orignal_node_id_to_internal_node_id_map[original_nx_node_id]

    def verify_graph_is_valid(self):

        # frm: TODO: Performance:  Only check verify_graph_is_valid() in development.
        #
        # For now, in order to assess performance differences between NX and RX
        # I will just return True...
        return True


        # Sanity check - this is where to add additional sanity checks in the future.

        # frm: TODO:  Enhance this routine to do more...

        # frm: TODO: Performance:  verify_graph_is_valid() is expensive - called a lot
        #
        # Come up with a way to run this in "debug mode" - that is, while in development/testing
        # but not in production.  It actually accounted for 5% of runtime...

        # Checks that there is one and only one graph
        if not (
            (self._nx_graph is not None and self._rx_graph is None)
            or (self._nx_graph is None and self._rx_graph is not None)
           ):
            raise Exception("Graph.verify_graph_is_valid - graph not properly configured")

    # frm: TODO: Performance:  is_nx_graph() and is_rx_graph() are expensive.
    #
    # Not all of the calls on these routines is needed in production - some are just
    # sanity checking.  Find a way to NOT run this code when in production.

    def is_nx_graph(self):
        # frm: TODO: Performance:  Only check graph_is_valid() in production
        #
        # Find a clever way to only run this code in development.  Commenting it out for now...
        #     self.verify_graph_is_valid()
        return self._nx_graph is not None

    def get_nx_graph(self):
        if not self.is_nx_graph():
            raise Exception("get_nx_graph - graph is not an NX version of Graph")
        return self._nx_graph

    def get_rx_graph(self):
        if not self.is_rx_graph():
            raise Exception("get_rx_graph - graph is not an RX version of Graph")
        return self._rx_graph

    def is_rx_graph(self):
        # frm: TODO: Performance:  Only check graph_is_valid() in production
        #
        # Find a clever way to only run this code in development.  Commenting it out for now...
        #     self.verify_graph_is_valid()
        return self._rx_graph is not None

    def convert_from_nx_to_rx(self) -> "Graph":
        # Return a Graph object which has a RustworkX Graph object as its
        # embedded graph object.
        #
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

                # frm: TODO:  Add a comment about the intended use of this routine to its 
                #               overview comment above.
                raise Exception("convert_from_nx_to_rx: graph to be converted is a subgraph")

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
            for node_id in converted_graph.nodes:
                original_nx_node_id = converted_graph.node_data(node_id)["__networkx_node__"]
                _node_id_to_original_nx_node_id_map[node_id] = original_nx_node_id
            converted_graph._node_id_to_original_nx_node_id_map = _node_id_to_original_nx_node_id_map

            return converted_graph
        elif self.is_rx_graph():
            return self
        else: 
            raise Exception("convert_from_nx_to_rx: Bad kind of Graph object")

    def get_nx_to_rx_node_id_map(self):
        # Simple getter method
        if not self.is_rx_graph():
            raise Exception("get_nx_to_rx_node_id_map: Graph is not an RX based Graph")

        return self.nx_to_rx_node_id_map

    @classmethod
    def from_json(cls, json_file: str) -> "Graph":
        # frm TODO:  Do we want to be able to go from JSON directly to RX?
        #
        # Peter said that this is not a priority - that we only need RX after
        # creating a partition, but maybe in the future if we decide to 
        # encourage an all RX world...
        #

        with open(json_file) as f:
            data = json.load(f)
        # frm: A bit of Python magic - an adjacency graph is a dict of dict of dicts
        #       which is structurally equivalent to a NetworkX graph, so you can just
        #       pretend that is what it is and it all works.
        nx_graph = json_graph.adjacency_graph(data)
        graph = cls.from_networkx(nx_graph)
        graph.issue_warnings()
        return graph 

    def to_json(self, json_file: str, include_geometries_as_geojson: bool = False) -> None:
        # frm TODO:  Implement this for an RX based graph
        if not self.is_nx_graph():
            raise Exception("At present, can only create JSON for NetworkX graph")

        data = json_graph.adjacency_data(self._nx_graph)

        if include_geometries_as_geojson:
            convert_geometries_to_geojson(data)
        else:
            remove_geometries(data)

        with open(json_file, "w") as f:
            json.dump(data, f, default=json_serialize)

    @classmethod
    def from_file(
        cls,
        filename: str,
        adjacency: str = "rook",
        cols_to_add: Optional[List[str]] = None,
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
        :type cols_to_add: Optional[List[str]], optional
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
        # frm: TODO:  Need to make sure this works for RX also
        #               To do so, need to find out how CRS data is used
        #               and whether it is used externally or only internally...
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
        cols_to_add: Optional[List[str]] = None,
        reproject: bool = False,
        ignore_errors: bool = False,
        crs_override: Optional[Union[str, int]] = None,
    ) -> "Graph":
        
        # frm: Changed to operate on a NetworkX.Graph object and then convert to a
        #       Graph object at the end of the function.

        """
        Creates the adjacency :class:`Graph` of geometries described by `dataframe`.
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
        :type cols_to_add: Optional[List[str]], optional
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
        # frm: TODO: Make it explicit that neighbors() above is adjacency.neighbors()

        # frm: Original Code:  graph = cls(adjacencies)
        nx_graph = networkx.Graph(adjacencies)

        # frm: TODO:  Need to grok what geometry is used for - it is used in partition.py.plot()
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

        # frm: TODO:  Rethink the name of add_boundary_perimeters - it acts on an nx_graph
        #               which seems wrong with the given name.  Maybe it should be:
        #               add_boundary_perimeters_to_nx_graph()
        #
        #               It raises the question of whether there should be an nx_utilities 
        #               module for stuff designed to only work on nx_graph objects.
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

    def lookup(self, node: Any, field: Any):
        # Not quite sure why this routine existed in the original graph.py
        # code, since most of the other code does not use it, and instead
        # does graph.nodes[node_id][key] - back when a Graph was a subclass
        # of NetworkX.Graph.  
        #
        # It is left because a couple of other files use it (versioneer.py, 
        # county_splits.py, and tally.py) and because perhaps an end user also
        # uses it.  Leaving it does not significant harm - it is just code bloat...

        # frm: TODO: Remove this routine: def lookup()  => in FrozenGraph too
        #
        # As per Peter's PR comment:
        #
        # Yeah, I will get rid of this in the future. This is very old code 
        # that someone probably wrote to make their life easier in the early 
        # stages of the package, but it's not really useful. I am going to be 
        # changing all of the old setup and versioning systems over to use UV 
        # anyway, and county_splits.py and tally.py are easy changes
        #

        return self.node_data(node, field)

    # Performance Note:  
    # 
    # Most of the functions in the Graph class will be called after a 
    # partition has been created and the underlying graph converted
    # to be based on RX.  So, by testing first for RX we actually
    # save a significant amount of time because we do not need to 
    # also test for NX (if you test for NX first then you do two tests).
    #

    @property
    def node_indices(self):
        self.verify_graph_is_valid()

        # frm: TODO:  This does the same thing that graph.nodes does - returning a list of node_ids.
        #               Do we really want to support two ways of doing the same thing?

        if (self.is_rx_graph()):
            return set(self._rx_graph.node_indices())
        elif (self.is_nx_graph()):
            return set(self._nx_graph.nodes)
        else:
            raise Exception("Graph.node_indices - bad kind of graph object")

    @property
    def edge_indices(self):
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # A set of edge_ids for the edges
            return set(self._rx_graph.edge_indices())
        elif (self.is_nx_graph()):
            # A set of edge_ids (tuples) extracted from the graph's EdgeView
            return set(self._nx_graph.edges)
        else:
            raise Exception("Graph.edges - bad kind of graph object")

    def get_edge_from_edge_id(self, edge_id):
        """
        In NX, an edge_id is a tuple of node_ids, but in RX an edge_id
        is an integer.  To get the tuple of node_ids in RX, you need to
        make a call using the edge_id.

        Stated differently, in NX an edge and an edge ID are the same, but
        not in RX...
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
            raise Exception("Graph.get_edge_from_edge_id - bad kind of graph object")

    def get_edge_id_from_edge(self, edge):
        """
        Another case where we need to deal with the fact that in 
        NX an edge ID is a tuple of node_ids, where in RX an edge ID
        is an integer assocaited with an edge.
        """
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
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
            raise Exception("Graph.get_edge_id_from_edge - bad kind of graph object")

    @property
    def nodes(self):
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # A list of integer node_ids
            return list(self._rx_graph.node_indices())
        elif (self.is_nx_graph()):
            # A list of node_ids -  
            return list(self._nx_graph.nodes)
        else:
            raise Exception("Graph.sdges - bad kind of graph object")

    @property
    def edges(self):
        # frm: TODO:  Confirm that this will work - returning different kinds of values

        """
        Edges are one of the areas where NX and RX differ.  

        Conceptually an edge is just a tuple identifying the two nodes comprising the edge.
        To be a little more specific, we will consider an edge to be a tuple of node_ids.

        But what is an edge_id?  In NX, the edge_id is just the tuple of node_ids.  I do 
        not know if NX is smart enough in an undirected graph to know that (3,4) is the same
        as (4,3), but I assume that it is.  In RX, however, the edge_id is just an integer.
        Stated differently, in NX there is no difference between an "edge" and an "edge_id", 
        but in RX there is.

        So, the new Graph object is going to distinguish between edges and edge_ids.
        Graph.edges will return a set of tuples in both cases, and Graph.edge_indices will
        return a set of edge_ids in both cases.  This is a little funky as the return type
        for Graph.edge_indices will be structurally different for NX and RX version of Graph
        objects, but hey - this is Python, so why not?  Sorry for the snide attack...

        Another issue (that should probably be documented elsewhere instead of here) is that
        in NX, Graph.edges returns an EdgeView object which allows for access to several 
        different bits of information about edges.  If you iterate over Graph.edges you
        get a sequence of tuples for the edges, but if you use square bracket notation, 
        as in: Graph.edges[(n1, n2)] you get access to the data dictionary for the edge.
        
        Here are some examples:
        
          for e in nx_graph.edges:
              print("This edge goes between the following nodes: ", e)
        
        The above will print out all of the edge_id tuples:
        
              This edge goes between nodes:  (46, 47)
              This edge goes between nodes:  (47, 55)
              This edge goes between nodes:  (48, 56)
              This edge goes between nodes:  (48, 49)
              ...
        
        However, if you want to get the data dictionary associated with the edge that goes
        between nodes 46, and 47, then you can do:
        
          print("node: (46,47) has data: ", nx_graph.edges[(46,47)])
        
              node: (46,47) has data:  {'weight': 5.5, 'total_population': 123445}
        
        RX does not support the EdgeView object, so we will use the same approach as for nodes.
        To get access to an edge's data dictionary, one will need to use the new function,
        edge_data(edge_id) - where edge_id will be either a tuple or an integer depending
        on what flavor of Graph is being operated on.
        """

        self.verify_graph_is_valid()

        # frm: TODO:  Think about whether edges() should return a set or a list.
        #
        # nodes() returns a list, so my first take is that edges() should do so
        # as well (or maybe nodes() should return a set).  Seems odd for them to return
        # different types...

        if (self.is_rx_graph()):
            # A set of tuples for the edges
            return set(self._rx_graph.edge_list())
        elif (self.is_nx_graph()):
            # A set of tuples extracted from the graph's EdgeView
            return set(self._nx_graph.edges)
        else:
            raise Exception("Graph.edges - bad kind of graph object")

    def add_edge(self, node_id1, node_id2):
        # frm: TODO:  Think about whether this routine makes sense for RX based Graph objects
        #
        # The current paradigm is that the user will use NX to create and modify graphs, but
        # then transition (automatically) to using RX once a Partition object is created.
        # This paradigm would not allow modifying an RX graph, so maybe (until we transition
        # to allowing folks to start with RX based Graph objects) we disallow this for RX
        # based graphs
        #

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # empty dict tells RX the edge data will be a dict 
            self._rx_graph.add_edge(node_id1, node_id2, {})
        elif (self.is_nx_graph()):
            self._nx_graph.add_edge(node_id1, node_id2)
        else:
            raise Exception("Graph.add_edge - bad kind of graph object")

    def get_edge_tuple(self, edge_id):

        # frm: TODO:  Delete this routine after verifying that nobody uses it.
        #
        # It appears that the gerrychain code does not use this.  Need to 
        # verify that it was added by me (and hence is not part of any 
        # external legacy code), but then it should be deleted as it is 
        # semantically the same as get_edge_from_edge_id()

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # frm: TODO: Performance:  There is probably a more efficnient way to do this
            return self._rx_graph.edge_list()[edge_id]
        elif (self.is_nx_graph()):
            # In NX, the edge_id is already a tuple with the two node_ids
            return edge_id
        else:
            raise Exception("Graph.get_edge_tuple - bad kind of graph object")

    def add_data(
        self,  df: pd.DataFrame, columns: Optional[Iterable[str]] = None
    ) -> None:
        """
        Add columns of a DataFrame to a graph as node attributes
        by matching the DataFrame's index to node ids.

        :param df: Dataframe containing given columns.
        :type df: :class:`pandas.DataFrame`
        :param columns: List of dataframe column names to add. Default is None.
        :type columns: Optional[Iterable[str]], optional

        :returns: None
        """

        if not (self.is_nx_graph()):
            raise Exception("Graph.add_data only valid for NetworkX based graphs")

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
        columns: Optional[List[str]] = None,
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
        :type columns: Optional[List[str]], optional
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

        if not self.is_nx_graph():
            raise Exception("Graph.join only valid for NetworkX based Graph objects")
        nx_graph = self._nx_graph

        if left_index is not None:
            ids_to_index = networkx.get_node_attributes(nx_graph, left_index)
        else:
            # When the left_index is node ID, the matching is just
            # a redundant {node: node} dictionary
            # frm: TODO:  don't think self.nodes works for RX...
            ids_to_index = dict(zip(self.nodes, self.nodes))

        node_attributes = {
            node_id: {
                column: values[index] for column, values in column_dictionaries.items()
            }
            for node_id, index in ids_to_index.items()
        }

        networkx.set_node_attributes(nx_graph, node_attributes)

    @property
    def islands(self):
        # Return all nodes of degree 0 (those not connected in an edge to another node)
        return set(node for node in self.node_indices if self.degree(node) == 0)

    def is_directed(self):
        # frm TODO:   Get rid of this hack.  I added it because code in contiguity.py 
        #               called nx.is_connected() which eventually called is_directed()
        #               assuming the graph was an nx_graph.
        return False
    
    def warn_for_islands(self) -> None:
        islands = self.islands
        if len(self.islands) > 0:
            warnings.warn(
                "Found islands (degree-0 nodes). Indices of islands: {}".format(islands)
        )
    
    def issue_warnings(self) -> None:
        self.warn_for_islands()

    # frm TODO: Implement a FrozenGraph that supports RX...
    #               self.graph.join = frozen
    #               self.graph.add_data = frozen
    #               self.size = len(self.graph)

    def __len__(self) -> int:
        # Relies on self.node_indices to work on both NX and RX
        return len(self.node_indices)

    def __getattr__(self, __name: str) -> Any:
        # frm: TODO:  Get rid of this eventually - it is very dangerous...

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

        # frm: TODO: Fix this hack - see comment above...
        if (__name == "_nx_graph") or (__name == "_rx_graph"):
            return None

        # If attribute doesn't exist on this object, try
        # its underlying graph object...
        if (self.is_rx_graph()):
            return object.__getattribute__(self._rx_graph, __name)
        elif (self.is_nx_graph()):
            return object.__getattribute__(self._nx_graph, __name)
        else:
            raise Exception("Graph.__getattribute__ - bad kind of graph object")

    def __getitem__(self, __name: str) -> Any:
        # frm: ???: TODO:   Does any of the code actually use this?
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
            # frm TODO:
            raise Exception("Graph.__getitem__() NYI for RX")
        elif (self.is_nx_graph()):
            return self._nx_graph[__name]
        else:
            raise Exception("Graph.__getitem__() - bad kind of graph object")

    def __iter__(self) -> Iterable[Any]:
        # frm: TODO:  Verify that this does the right thing...
        #               It seems to do the right thing - iterating over node_ids which
        #               works so long as NX uses integers for node_ids.  
        # frm: TODO:    Perhaps I should test for non-integer node_ids in NX graphs and issue a warning...
        #               In any event, this deserves thought: what to do for NX graphs that do not use
        #               integers for node_ids?
        yield from self.node_indices

    def subgraph(self, nodes: Iterable[Any]) -> "Graph":
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
            # frm TODO:  Need to check logic below - not sure this works exactly correctly for RX...
            if isinstance(nodes, frozenset) or isinstance(nodes, set):
                nodes = list(nodes)
            # For RX, the node_ids in the subgraph change, so we need a way to map subgraph node_ids 
            # into parent graph node_ids.  To do so, we add the parent node_id into the node data
            # so that in the subgraph we can find it and then create the map.
            # frm: TODO:  Be careful - node data is shared by subgraphs, so a subgraph of this
            #               subgraph will still have this field set - meaning that the field's
            #               value is not dependable over time - perhaps I should null it out
            #               after using it here...
            for node_id in nodes:
                self.node_data(node_id)["parent_node_id"] = node_id
            
            # frm: TODO:  Since data is shared by nodes in subgraphs, perhaps we could just set
            #               the "original_nx_node_id" in the beginning and rely on it forever...
            #
            # This actually gives me the heebie-jeebies - we have aliased data that we are overwriting.
            # Either it is aliased data and we count on that and don't bother to update it, or else
            # we ensure that it is NOT aliased data and then we can feel free to overwrite it and/or
            # set it anew...
            #
            # In short, verify that data in subgraphs is shared (in RX) and then think to make sure
            # that we do NOT need to set this value, because it is already set.
            #
            # A more general issue is whether it is OK for data in subgraphs to be shared.  I think
            # so because we do not store any temporary or context dependent information in node-data
            # but it would be nice to validate that (and ideally to test it).  At the very least
            # if subgraph data (and in fact NX and RX node data) is shared, then that should be documented
            # up the wazoo...
            #
            for node_id in nodes:
                self.node_data(node_id)["original_nx_node_id"] = self._node_id_to_original_nx_node_id_map[node_id]

            rx_subgraph = self._rx_graph.subgraph(nodes)
            new_subgraph = self.from_rustworkx(rx_subgraph)

            # frm: Create the map from subgraph node_id to parent graph node_id
            _node_id_to_parent_node_id_map = {}
            for subgraph_node_id in new_subgraph.node_indices:
                _node_id_to_parent_node_id_map[subgraph_node_id] = new_subgraph.node_data(subgraph_node_id)["parent_node_id"]
            # frm: Create the map from subgraph node_id to the original graph's node_id
            _node_id_to_original_nx_node_id_map = {}
            for subgraph_node_id in new_subgraph.node_indices:
                _node_id_to_original_nx_node_id_map[subgraph_node_id] = new_subgraph.node_data(subgraph_node_id)["original_nx_node_id"]

        else:
            raise Exception("Graph.subgraph - bad kind of graph object")

        new_subgraph._is_a_subgraph = True
        new_subgraph._node_id_to_parent_node_id_map = _node_id_to_parent_node_id_map
        new_subgraph._node_id_to_original_nx_node_id_map = _node_id_to_original_nx_node_id_map

        return new_subgraph

    def translate_subgraph_node_ids_for_flips(self, flips):
        # flips is a dictionary mapping node_ids to parts (districts).
        # This routine replaces the node_ids of the subgraph with the node_ids
        # for the same node in the parent graph.  This routine is used to
        # when a computation is made on a subgraph but the resulting flips
        # being returned want to be the appropriate node_ids for the parent graph.
        translated_flips = {}
        for subgraph_node_id, part in flips.items():
            parent_node_id = self._node_id_to_parent_node_id_map[subgraph_node_id]
            translated_flips[parent_node_id] = part

        return translated_flips

    def translate_subgraph_node_ids_for_set_of_nodes(self, set_of_nodes):
        # This routine replaces the node_ids of the subgraph with the node_ids
        # for the same node in the parent graph.  This routine is used to
        # when a computation is made on a subgraph but the resulting set of nodes
        # being returned want to be the appropriate node_ids for the parent graph.
        translated_set_of_nodes = set()
        for node_id in set_of_nodes:
            translated_set_of_nodes.add(self._node_id_to_parent_node_id_map[node_id])
        return translated_set_of_nodes

    def generic_bfs_edges(self, source, neighbors=None, depth_limit=None):
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
                        yield parent, child
                if len(seen) == n:
                    return
            depth += 1

    # frm: TODO:  Add tests for all of the new routines I have added...

    def generic_bfs_successors_generator(self, root_node_id):
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
    
    def generic_bfs_successors(self, root_node_id):
        return dict(self.generic_bfs_successors_generator(root_node_id))

    def generic_bfs_predecessors(self, root_node_id):
        # frm Note:  We had do implement our own, because the built-in RX version only worked 
        #               for directed graphs.
        predecessors = []
        for s, t in self.generic_bfs_edges(root_node_id):
            predecessors.append((t,s))
        return dict(predecessors)


    def predecessors(self, root_node_id):

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

        TODO: Decide if it makes sense to have different implementations 
              for NX and RX.  The code below has the original definition
              from the pre-RX codebase, but the code for RX will work 
              for NX too - so I think that there is no good reason to
              have different code for NX. Maybe no harm, but on the other
              hand, it seems like a needless difference and hence more 
              complexity...
        """

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            return self.generic_bfs_predecessors(root_node_id)
        elif (self.is_nx_graph()):
            return {a: b for a, b in networkx.bfs_predecessors(self._nx_graph, root_node_id)}
        else:
            raise Exception("Graph.predecessors - bad kind of graph object")

    def successors(self, root_node_id):
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            return self.generic_bfs_successors(root_node_id)
        elif (self.is_nx_graph()):
            return {a: b for a, b in networkx.bfs_successors(self._nx_graph, root_node_id)}
        else:
            raise Exception("Graph.successors - bad kind of graph object")

    def neighbors(self, node):
        self.verify_graph_is_valid()

        # NX  neighbors() returns a <dict_keyiterator> which iterates over the node_ids of neighbor nodes
        # RX  neighbors() returns a NodeIndices object with the list of node_ids of neighbor nodes
        # However, the code outside graph.py only ever iterates over all neighbors so returning a list works...
        if (self.is_rx_graph()):
            # frm: TODO: Performance:  Do not convert to a list
            #
            # The RX path (this path) is much more expensive than the NX path, and
            # I am assuming that it is the conversion to a list in the original code
            # that is expensive, so I am going to just not convert it to a list
            # since the return type of rx.neighbors() is a NodeIndices object which
            # is already essentially a Python list - in that it implements the Python sequence protocol
            #
            # Original code:
            #     return list(self._rx_graph.neighbors(node))
            return self._rx_graph.neighbors(node)
        elif (self.is_nx_graph()):
            return list(self._nx_graph.neighbors(node))
        else:
            raise Exception("Graph.neighbors - bad kind of graph object")

    def degree(self, node: Any) -> int:
        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            return self._rx_graph.degree(node)
        elif (self.is_nx_graph()):
            return self._nx_graph.degree(node)
        else:
            raise Exception("Graph.degree - bad kind of graph object")

    def node_data(self, node_id):
        # This routine returns the data dictionary for the given node's data

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            data_dict = self._rx_graph[node_id]
        elif (self.is_nx_graph()):
            data_dict = self._nx_graph.nodes[node_id]
        else:
            raise Exception("Graph.node_data - bad kind of graph object")

        if not isinstance(data_dict, dict):
            raise Exception("node data is not a dictionary");
        
        return data_dict

    def edge_data(self, edge_id):
        # This routine returns the data dictionary for the given edge's data

        """
        CLEVERNESS ALERT!
        
        The type of the edge_id parameter will be a tuple in the case of an 
        embedded NX graph but will be an integer in the case of an RX embedded
        graph.
        
        """

        self.verify_graph_is_valid()

        if (self.is_rx_graph()):
            # frm: TODO: Performance: use get_edge_data_by_index()
            #
            # Original code (pre October 2025) that indexed into all edges => slow
            #     data_dict = self._rx_graph.edges()[edge_id]
            data_dict = self._rx_graph.get_edge_data_by_index(edge_id)
        elif (self.is_nx_graph()):
            data_dict = self._nx_graph.edges[edge_id]
        else:
            raise Exception("Graph.edge_data - bad kind of graph object")

        if not isinstance(data_dict, dict):
            raise Exception("edge data is not a dictionary");
        
        return data_dict


    # frm: Note:  I added the laplacian_matrix routines as methods of the Graph
    #               class because they are only ever used on Graph objects.  It
    #               bloats the Graph class, but it still seems like the best
    #               option.

    def laplacian_matrix(self):
        # A local "gc" (as in GerryChain) version of the laplacian matrix

        # frm: TODO:  The NX version returns a matrix of integer values while the
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
            raise Exception("laplacian_matrix: badly configured graph parameter")

        return laplacian_matrix

    def normalized_laplacian_matrix(self):

        def create_scipy_sparse_array_from_rx_graph(rx_graph):
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
            # I have left debugging print statements (commented out) in case someone in the future
            # (probably me) wants to verify that the right things are happening...

            # Original NetworkX Code:    
            #     A = networkx.to_scipy_sparse_array(G, nodelist=nodelist, weight=weight, format="csr")
            #
            A = create_scipy_sparse_array_from_rx_graph(rx_graph)
            n, _ = A.shape          # shape() => dimensions of the array (rows, cols), so n = num_rows
            # print("")
            # print(f"normalized_laplacian_matrix: num_rows = {n}")
            # print(f"normalized_laplacian_matrix: sparse_array is: {A}")
            diags = A.sum(axis=1)   # sum of values in each row => column vector
            diags = diags.T         # convert to a row vector / 1D array
            # print(f"normalized_laplacian_matrix: diags is: \n{diags}")
            D = scipy.sparse.dia_array((diags, [0]), shape=(n, n)).tocsr()
            # print(f"normalized_laplacian_matrix: D is: \n{D}")
            L = D - A
            # print(f"normalized_laplacian_matrix: L is: \n{L}")
            with numpy.errstate(divide="ignore"):
                diags_sqrt = 1.0 / numpy.sqrt(diags)
            diags_sqrt[numpy.isinf(diags_sqrt)] = 0
            # print(f"normalized_laplacian_matrix: diags_sqrt is: \n{diags_sqrt}")
            DH = scipy.sparse.dia_array((diags_sqrt, 0), shape=(n, n)).tocsr()
            # print(f"normalized_laplacian_matrix: DH is: \n{DH}")
            normalized_laplacian = DH @ (L @ DH)
            # print(f"normalized_laplacian_matrix: normalized_laplacian is: \n{normalized_laplacian}")
            return normalized_laplacian

        elif self.is_nx_graph():
            nx_graph = self._nx_graph
            laplacian_matrix = networkx.normalized_laplacian_matrix(nx_graph)
        else:
            raise Exception("normalized_laplacian_matrix: badly configured graph parameter")

        return laplacian_matrix

    def subgraphs_for_connected_components(self):
        # Create a list of subgraphs - one for each subset of connected nodes in the graph
        #
        # This mirrors the nx.connected_components() routine in NetworkX

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
            raise Exception("subgraphs_for_connected_components: Bad kind of Graph")
        
        return subgraphs

    def num_connected_components(self):
        if self.is_rx_graph():
            rx_graph = self.get_rx_graph()
            connected_components = rustworkx.connected_components(rx_graph)
        elif self.is_nx_graph():
            nx_graph = self.get_nx_graph()
            connected_components = list(networkx.connected_components(nx_graph))
        else:
            raise Exception("num_connected_components: Bad kind of Graph")

        num_cc = len(connected_components)
        return num_cc

    def is_a_tree(self):
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
            raise Exception("is_a_tree: Bad kind of Graph")

######################################################

class OriginalGraph(networkx.Graph):
    """
    frm: This is the original code for gerrychain.Graph before any RustworkX changes.

    It continues to exist so that I can write tests to verify that from the outside
    the new Graph object behaves the same as the original Graph object.

    See the test in tests/frm_tests/test_frm_old_vs_new_graph.py
    """

    # frm: Original Graph code...
    def __repr__(self):
        return "<Graph [{} nodes, {} edges]>".format(len(self.nodes), len(self.edges))

    # frm: Original Graph code...
    @classmethod
    def from_networkx(cls, graph: networkx.Graph) -> "Graph":
        """
        Create a Graph instance from a networkx.Graph object.

        :param graph: The networkx graph to be converted.
        :type graph: networkx.Graph

        :returns: The converted graph as an instance of this class.
        :rtype: Graph
        """
        g = cls(graph)
        return g

    # frm: Original Graph code...
    @classmethod
    def from_json(cls, json_file: str) -> "Graph":
        """
        Load a graph from a JSON file in the NetworkX json_graph format.

        :param json_file: Path to JSON file.
        :type json_file: str

        :returns: The loaded graph as an instance of this class.
        :rtype: Graph
        """
        with open(json_file) as f:
            data = json.load(f)
        g = json_graph.adjacency_graph(data)
        graph = cls.from_networkx(g)
        graph.issue_warnings()
        return graph

    # frm: Original Graph code...
    def to_json(
        self, json_file: str, *, include_geometries_as_geojson: bool = False
    ) -> None:
        """
        Save a graph to a JSON file in the NetworkX json_graph format.

        :param json_file: Path to target JSON file.
        :type json_file: str
        :param bool include_geometry_as_geojson: Whether to include
            any :mod:`shapely` geometry objects encountered in the graph's node
            attributes as GeoJSON. The default (``False``) behavior is to remove
            all geometry objects because they are not serializable. Including the
            GeoJSON will result in a much larger JSON file.
        :type include_geometries_as_geojson: bool, optional

        :returns: None
        """
        data = json_graph.adjacency_data(self)

        if include_geometries_as_geojson:
            convert_geometries_to_geojson(data)
        else:
            remove_geometries(data)

        with open(json_file, "w") as f:
            json.dump(data, f, default=json_serialize)

    # frm: Original Graph code...
    @classmethod
    def from_file(
        cls,
        filename: str,
        adjacency: str = "rook",
        cols_to_add: Optional[List[str]] = None,
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
        :type cols_to_add: Optional[List[str]], optional
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

        graph.graph["crs"] = df.crs.to_json()
        return graph

    # frm: Original Graph code...
    @classmethod
    def from_geodataframe(
        cls,
        dataframe: pd.DataFrame,
        adjacency: str = "rook",
        cols_to_add: Optional[List[str]] = None,
        reproject: bool = False,
        ignore_errors: bool = False,
        crs_override: Optional[Union[str, int]] = None,
    ) -> "Graph":
        """
        Creates the adjacency :class:`Graph` of geometries described by `dataframe`.
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
        :type cols_to_add: Optional[List[str]], optional
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
        graph = cls(adjacencies)

        graph.geometry = df.geometry

        graph.issue_warnings()

        # Add "exterior" perimeters to the boundary nodes
        add_boundary_perimeters(graph, df.geometry)

        # Add area data to the nodes
        areas = df.geometry.area.to_dict()
        networkx.set_node_attributes(graph, name="area", values=areas)

        graph.add_data(df, columns=cols_to_add)

        if crs_override is not None:
            df.set_crs(crs_override, inplace=True)

        if df.crs is None:
            warnings.warn(
                "GeoDataFrame has no CRS. Did you forget to set it? "
                "If you're sure this is correct, you can ignore this warning. "
                "Otherwise, please set the CRS using the `crs_override` parameter. "
                "Attempting to proceed without a CRS."
            )
            graph.graph["crs"] = None
        else:
            graph.graph["crs"] = df.crs.to_json()

        return graph

    # frm: Original Graph code...
    def lookup(self, node: Any, field: Any) -> Any:
        """
        Lookup a node/field attribute.

        :param node: Node to look up.
        :type node: Any
        :param field: Field to look up.
        :type field: Any

        :returns: The value of the attribute `field` at `node`.
        :rtype: Any
        """
        return self.nodes[node][field]

    # frm: Original Graph code...
    @property
    def node_indices(self):
        return set(self.nodes)

    # frm: Original Graph code...
    @property
    def edge_indices(self):
        return set(self.edges)

    # frm: Original Graph code...
    def add_data(
        self, df: pd.DataFrame, columns: Optional[Iterable[str]] = None
    ) -> None:
        """
        Add columns of a DataFrame to a graph as node attributes
        by matching the DataFrame's index to node ids.

        :param df: Dataframe containing given columns.
        :type df: :class:`pandas.DataFrame`
        :param columns: List of dataframe column names to add. Default is None.
        :type columns: Optional[Iterable[str]], optional

        :returns: None
        """

        if columns is None:
            columns = list(df.columns)

        check_dataframe(df[columns])

        column_dictionaries = df.to_dict("index")
        networkx.set_node_attributes(self, column_dictionaries)

        if hasattr(self, "data"):
            self.data[columns] = df[columns]  # type: ignore
        else:
            self.data = df[columns]

    # frm: Original Graph code...
    def join(
        self,
        dataframe: pd.DataFrame,
        columns: Optional[List[str]] = None,
        left_index: Optional[str] = None,
        right_index: Optional[str] = None,
    ) -> None:
        """
        Add data from a dataframe to the graph, matching nodes to rows when
        the node's `left_index` attribute equals the row's `right_index` value.

        This is the same as a "join" in SQL:
          insert into <graph> 
            select <> from <dataframe>
            where <graph>.

        :param dataframe: DataFrame.
        :type dataframe: :class:`pandas.DataFrame`
        :columns: The columns whose data you wish to add to the graph.
            If not provided, all columns are added. Default is None.
        :type columns: Optional[List[str]], optional
        :left_index: The node attribute used to match nodes to rows.
            If not provided, node IDs are used. Default is None.
        :type left_index: Optional[str], optional
        :right_index: The DataFrame column name to use to match rows
            to nodes. If not provided, the DataFrame's index is used. Default is None.
        :type right_index: Optional[str], optional

        :returns: None
        """
        # frm: TODO:  Implement this for RX.  Note, however, that this is probably
        #               low priority since this routine is for building a graph
        #               which for now (summer 2025) will continue to be done using
        #               NetworkX.  That is, this code will not be used after 
        #               freezing the graph when we create a Parition...
        if (not self.is_nx_graph()):
            raise Exception("join(): Not supported for RX based Graph objects")

        if right_index is not None:
            df = dataframe.set_index(right_index)
        else:
            df = dataframe

        if columns is not None:
            df = df[columns]

        check_dataframe(df)

        # Transform the dataframe into a dict of dicts, where
        # each column in the df is associated with a dict of
        # <row_id>: <column_value> values.
        column_dictionaries = df.to_dict()

        # Determine what data in the graph to sync up with the
        # data in the dataframe.  ids_to_index maps node_ids to
        # values that select which row in dataframe should be
        # associated with that node_id.
        if left_index is not None:
            # frm: TODO:  Figure out how to make this work for RX...
            ids_to_index = networkx.get_node_attributes(self, left_index)
        else:
            # When the left_index is node ID, the matching is just
            # a redundant {node: node} dictionary
            ids_to_index = dict(zip(self.nodes, self.nodes))

        # For each column in the dataframe, extract the appropriate entry for 
        # the given node_id (using index) and wrap it all up in a dict.  The 
        # result is a dict of (name, value) pairs of data from the dataframe
        # for each node_id.
        node_attributes = {
            node_id: {
                column: values[index] for column, values in column_dictionaries.items()
            }
            for node_id, index in ids_to_index.items()
        }

        # frm: TODO:  Figure out how to make this work for RX...
        networkx.set_node_attributes(self, node_attributes)

    # frm: Original Graph code...
    @property
    def islands(self) -> Set:
        """
        :returns: The set of degree-0 nodes.
        :rtype: Set
        """
        return set(node for node in self if self.degree[node] == 0)

    # frm: Original Graph code...
    def warn_for_islands(self) -> None:
        """
        :returns: None

        :raises: UserWarning if the graph has any islands (degree-0 nodes).
        """
        islands = self.islands
        if len(self.islands) > 0:
            warnings.warn(
                "Found islands (degree-0 nodes). Indices of islands: {}".format(islands)
            )

    # frm: Original Graph code...
    def issue_warnings(self) -> None:
        """
        :returns: None

        :raises: UserWarning if the graph has any red flags (right now, only islands).
        """
        self.warn_for_islands()

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

    # frm: TODO:  Think about whether it is reasonable to require this to work
    #               on an NetworkX.Graph object.

    # frm: The original code operated on the Graph object which was a subclass of
    #       NetworkX.Graph.  I have changed it to operate on a NetworkX.Graph object
    #       with the understanding that callers will reach down into a Graph object
    #       and pass in the inner nx_graph data member.

    if not(isinstance(nx_graph, networkx.Graph)):
        raise Exception("add_boundary_permiters: Graph is not a NetworkX.Graph object")

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

    # frm: TODO:   Rename the internal data member, "graph", to be something else.
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

        # frm TODO: Add logic to have this work for RX.

        self.graph = graph
        # frm: TODO:  Not sure this works for RX
        self.size = len(self.graph.nodes)

    def __len__(self) -> int:
        return self.size

    def __getattribute__(self, __name: str) -> Any:
        try:
            return object.__getattribute__(self, __name)
        except AttributeError:
            # delegate getting the attribute to the graph data member
            return self.graph.__getattribute__(__name)

    def __getitem__(self, __name: str) -> Any:
        return self.graph[__name]

    def __iter__(self) -> Iterable[Any]:
        yield from self.node_indices

    @functools.lru_cache(16384)
    def neighbors(self, n: Any) -> Tuple[Any, ...]:
        # frm: Original Code:
        #    return tuple(self.graph.neighbors(n))
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

    @functools.lru_cache(65536)
    def lookup(self, node: Any, field: str) -> Any:
        # frm: Original Code:   return self.graph.nodes[node][field]
        return self.node_data(node)[field]

    def subgraph(self, nodes: Iterable[Any]) -> "FrozenGraph":
        return FrozenGraph(self.graph.subgraph(nodes))
