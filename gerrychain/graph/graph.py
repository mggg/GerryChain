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

#########################################################
# frm Overview of changes (May 2025):
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

import networkx
from networkx.classes.function import frozen
from networkx.readwrite import json_graph
import pandas as pd

# frm: added to support RustworkX graphs (in the future)
import rustworkx

from .adjacency import neighbors
from .geo import GeometryError, invalid_geometries, reprojected
from typing import List, Iterable, Optional, Set, Tuple, Union


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

    # frm TODO: graph.nodes     This is inherited from NetworkX and is of type NodeView which
    #                           raises some interesting issues, because NodeView supports several
    #                           clever ways to access nodes (with one index and with two and maybe with three).  
    #                           I need to think about what this means for RX compatibility.  If users take advantage
    #                           of the different ways to access NodeView then I might need to implement something
    #                           similar for this new Graph class.  *sigh*
    #
    #                           The same concerns exist for EdgeView...
    #

    # frm:      This class cannot have a constructor - because there is code that assumes
    #           that it can use the default constructor to create instances of it.
    #           That code is buried deep in non GerryChain code, so I don't really understand
    #           what it is doing, but the assignment of nxgraph and rxgraph class attributes/members
    #           needs to happen in the "from_xxx()" routines.
    #
    # def __init__(self, nxgraph: networkx.Graph, rxgraph: rustworkx.PyGraph)  -> None:
    #     # frm TODO:  check that exactly one param is not None - need one and only one graph...
    #     self.nxgraph = nxgraph
    #     self.rxgraph = rxgraph

    # frm: TODO:  Change nxgraph and rxgraph to be _nxgraph and _rxgraph

    # frm: TODO:    Add documentation for new data members I am adding:
    #               nxgraph, rxgraph, parent_node_id_map, is_a_subgraph

    @classmethod
    def from_networkx(cls, nxgraph: networkx.Graph) -> "Graph":
        graph = cls()
        graph.nxgraph = nxgraph
        graph.rxgraph = None
        graph.is_a_subgraph = False         # See comments on RX subgraph issues.
        graph.parent_node_id_map = {node: node for node in graph.node_indices}   # Identity map for top-level graph
        return graph
    
    @classmethod
    def from_rustworkx(cls, rxgraph: rustworkx.PyGraph) -> "Graph":
        graph = cls()   
        graph.rxgraph = rxgraph
        graph.nxgraph = None
        graph.is_a_subgraph = False         # See comments on RX subgraph issues.
        graph.parent_node_id_map = {node: node for node in graph.node_indices}   # Identity map for top-level graph
        return graph

    def hasOneGraph(self):
        # Checks that there is one and only one graph
        if (
            (self.nxgraph is not None and self.rxgraph is None)
            or (self.nxgraph is None and self.rxgraph is not None)
           ):
            return True
        else:
            return False

    def verifyGraphIsValid(self):
        # Sanity check
        if (not self.hasOneGraph()):
            raise Exception("Graph.edges - graph not properly configured")

    def isNxGraph(self):
        self.verifyGraphIsValid()
        return self.nxgraph is not None

    # frm TODO: Remove these once NX dependencies have been removed from tree.py (and other places?)
    #           Actually, this may be useful if end users have code that needs to operate on
    #           an NX Graph object...
    def getNxGraph(self):
        if not self.isNxGraph():
            raise Exception("getNxGraph - graph is not an NX version of Graph")
        return self.nxgraph

    def getRxGraph(self):
        if not self.isRxGraph():
            raise Exception("getRxGraph - graph is not an RX version of Graph")
        return self.rxgraph

    def isRxGraph(self):
        self.verifyGraphIsValid()
        return self.rxgraph is not None

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
        self.verifyGraphIsValid()
        if self.isNxGraph():
            rxgraph = rustworkx.networkx_converter(self.nxgraph, keep_attributes=True)
            return Graph.from_rustworkx(rxgraph)
        elif self.isRxGraph():
            return self
        else: 
            raise Exception("convert_from_nx_to_rx: Bad kind of Graph object")

    @classmethod
    def from_json(cls, json_file: str) -> "Graph":
        # frm TODO:  Do we want to be able to go from JSON directly to RX?
        with open(json_file) as f:
            data = json.load(f)
        # frm: A bit of Python magic - an adjacency graph is a dict of dict of dicts
        #       which is structurally equivalent to a NetworkX graph, so you can just
        #       pretend that is what it is and it all works.
        nxgraph = json_graph.adjacency_graph(data)
        graph = cls.from_networkx(nxgraph)
        graph.issue_warnings()
        return graph 

    def to_json(self, json_file: str, include_geometries_as_geojson: bool = False) -> None:
        # frm TODO:  Implement this for an RX based graph
        if self.nxgraph is None:
            raise Exception("At present, can only create JSON for NetworkX graph")

        data = json_graph.adjacency_data(self.nxgraph)

        if include_geometries_as_geojson:
            convert_geometries_to_geojson(data)
        else:
            remove_geometries(data)

        with open(json_file, "w") as f:
            json.dump(data, f, default=json_serialize)

    @classmethod
    def from_file():
        # frm TODO:  Copy the code for this 
        raise Exception("Graph.from_file NYI")

    @classmethod
    def from_geodataframe():
        # frm TODO:  Copy the code for this 
        raise Exception("Graph.from_geodataframe NYI")
    
    def lookup(self, node: Any, field: Any):
        # Not quite sure why this routine existed in the original graph.py
        # code, since most of the other code does not use it, and instead
        # does graph.nodes[node_id][key] - back when a Graph was a subclass
        # of NetworkX.Graph.  
        #
        # It is left because a couple of other files use it (versioneer.py, 
        # county_splits.py, and tally.py) and because perhaps an end user also
        # uses it.  Leaving it does not significant harm - it is just code bloat...
        return self.get_node_data_dict(node, field)

    @property
    def node_indices(self):
        self.verifyGraphIsValid()

        # frm: TODO:  This does the same thing that graph.nodes does - returning a list of node_ids.
        #               Do we really want to support two ways of doing the same thing?

        if (self.isNxGraph()):
            return set(self.nxgraph.nodes)
        elif (self.isRxGraph()):
            return set(self.rxgraph.node_indices())
        else:
            raise Exception("Graph.node_indices - bad kind of graph object")

    @property
    def edge_indices(self):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            # A set of edge_ids (tuples) extracted from the graph's EdgeView
            return set(self.nxgraph.edges)
        elif (self.isRxGraph()):
            # A set of edge_ids for the edges
            return set(self.rxgraph.edge_indices())
        else:
            raise Exception("Graph.edges - bad kind of graph object")

    # frm: TODO: Come up with a better name than this...
    def get_edge_from_edge_id(self, edge_id):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            # In NX, the edge_id is also the edge tuple
            return edge_id
        elif (self.isRxGraph()):
            # In RX, we need to go get the edge tuple
            return self.rxgraph.edge_list()[edge_id]
        else:
            raise Exception("Graph.get_edge_from_edge_id - bad kind of graph object")

    # frm: TODO: Come up with a better name than this...
    def get_edge_id_from_edge(self, edge):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            # In NX, the edge_id is also the edge tuple
            return edge
        elif (self.isRxGraph()):
            # In RX, we need to go get the edge_id from the edge tuple
            # frm: TODO:  Think about whether there is a better way to do this.  I am 
            #               worried that this might be expensive in terms of performance
            #               with large graphs.  This is used in tree.py when seeing if a
            #               cut edge has a weight assigned to it.
            # frm: Note that we sort both the edge_list and the edge, to canonicalize
            #       the edges so the smaller node_id is first.  This allows us to not 
            #       worry about whether the edge was (3,5) or (5,3)

            # frm: DBG: TODO: Remove debugging code
            # print("Graph.get_edge_id_from_edge: RX edge_list: ", list(self.rxgraph.edge_list()))
            # print(" ")
            sorted_edge_list = sorted(list(self.rxgraph.edge_list()))
            # print("Graph.get_edge_id_from_edge: sorted RX edge_list: ", sorted_edge_list)
            # print(" ")
            # frm: TODO:  There has to be a more elegant way to do this...  *sheesh*
            sorted_edge = edge
            if edge[0] > edge[1]:
                sorted_edge = (edge[1], edge[0])
            # print("Graph.get_edge_id_from_edge: edge and sorted_edge: ", edge, ", ", sorted_edge)
            # print(" ")
            return sorted_edge_list.index(sorted_edge)
        else:
            raise Exception("Graph.get_edge_id_from_edge - bad kind of graph object")

    @property
    def nodes(self):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            # A list of node_ids -  
            return list(self.nxgraph.nodes)
        elif (self.isRxGraph()):
            # A list of integer node_ids
            return list(self.rxgraph.node_indices())
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
        
          for e in nxgraph.edges:
              print("This edge goes between the following nodes: ", e)
        
        The above will print out all of the edge_id tuples:
        
              This edge goes between nodes:  (46, 47)
              This edge goes between nodes:  (47, 55)
              This edge goes between nodes:  (48, 56)
              This edge goes between nodes:  (48, 49)
              ...
        
        However, if you want to get the data dictionary associated with the edge that goes
        between nodes 46, and 47, then you can do:
        
          print("node: (46,47) has data: ", nxgraph.edges[(46,47)])
        
              node: (46,47) has data:  {'weight': 5.5, 'total_population': 123445}
        
        RX does not support the EdgeView object, so we will use the same approach as for nodes.
        To get access to an edge's data dictionary, one will need to use the new function,
        get_edge_data_dict(edge_id) - where edge_id will be either a tuple or an integer depending
        on what flavor of Graph is being operated on.
        """

        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            # A set of tuples extracted from the graph's EdgeView
            return set(self.nxgraph.edges)
        elif (self.isRxGraph()):
            # A set of tuples for the edges
            return set(self.rxgraph.edge_list())
        else:
            raise Exception("Graph.edges - bad kind of graph object")

    def add_edge(self, node_id1, node_id2):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            self.nxgraph.add_edge
        elif (self.isRxGraph()):
            # empty dict tells RX the edge data will be a dict 
            self.rxgraph.add_edge(node_id1, node_id2, {})
        else:
            raise Exception("Graph.add_edge - bad kind of graph object")

    def get_edge_tuple(self, edge_id):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            # In NX, the edge_id is already a tuple with the two node_ids
            return edge_id
        elif (self.isRxGraph()):
            return self.rxgraph.edge_list()[edge_id]
        else:
            raise Exception("Graph.get_edge_tuple - bad kind of graph object")

    def add_data():
        # frm TODO:
        raise Exception("Graph.add_data NYI")

    def join():
        # frm TODO:
        raise Exception("Graph.join NYI")

    @property
    def islands(self):
        # Return all nodes of degree 0 (those not connected in an edge to another node)
        return set(node for node in self.node_indices if self.degree(node) == 0)

    def is_directed(self):
        # frm TODO:   Get rid of this hack.  I added it because code in contiguity.py 
        #               called nx.is_connected() which eventually called is_directed()
        #               assuming the graph was an nxgraph.
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

        # If attribute doesn't exist on this object, try
        # its underlying graph object...
        if (self.isNxGraph()):
            return object.__getattribute__(self.nxgraph, __name)
        elif (self.isRxGraph()):
            return object.__getattribute__(self.rxgraph, __name)
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
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return self.nxgraph[__name]
        elif (self.isRxGraph()):
            # frm TODO:
            raise Exception("Graph.__getitem__() NYI for RX")
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
        involving node_ids to the caller.  To solve this, we define a parent_node_id_map whenever
        we create a subgraph that will provide the node_id in the parent for each node in the subgraph.
        For NX this is a no-op, and the parent_node_id_map is just an identity map - each node_id is 
        mapped to itself.  For RX, however, we store the parent_node_id in the node's data before
        creating the subgraph, and then in the subgraph, we use the parent's node_id to construct 
        a map from the subgraph node_id to the parent_node_id.

        This means that any function that wants to return results involving node_ids can safely
        just translate node_ids using the parent_node_id_map, so that the results make sense in
        the caller's context.

        A note of caution: if the caller retains the subgraph after using it in a function call, 
        the caller should almost certainly not use the node_ids in the subgraph for ANYTHING.
        It would be safest to reset the value of the subgraph to None after using it as an
        argument to a function call.

        Also, for both RX and NX, we set the parent_node_id_map to be the identity map for top-level
        graphs on the off chance that there is a function that takes both top-level graphs and 
        subgraphs as a parameter.  This allows the function to just always do the node translation.
        In the case of a top-level graph the translation will be a no-op, but it will be correct.

        Also, we set the is_a_subgraph = True, so that we can detect whether a parameter passed into
        a function is a top-level graph or not.  This will allow us to debug the code to determine 
        if assumptions about a parameter always being a subgraph is accurate.  It also helps to 
        educate future readers of the code that subgraphs are "interesting"...

        """

        self.verifyGraphIsValid()

        new_subgraph = None

        if (self.isNxGraph()):
            nx_subgraph = self.nxgraph.subgraph(nodes)
            new_subgraph = self.from_networkx(nx_subgraph)
            # for NX, the node_ids in subgraph are the same as in the parent graph
            parent_node_id_map = {node: node for node in nodes}
        elif (self.isRxGraph()):
            # frm TODO:  Need to check logic below - not sure this works exactly correctly for RX...
            # print("Graph.subgraph(): type of nodes before cast to list is: ", type(nodes))
            if isinstance(nodes, frozenset) or isinstance(nodes, set):
                nodes = list(nodes)
                # print("Graph.subgraph(): type of nodes after cast to list is: ", type(nodes))
            # For RX, the node_ids in the subgraph change, so we need a way to map subgraph node_ids 
            # into parent graph node_ids.  To do so, we add the parent node_id into the node data
            # so that in the subgraph we can find it and then create the map.
            for node_id in nodes:
                self.get_node_data_dict(node_id)["parent_node_id"] = node_id

            rx_subgraph = self.rxgraph.subgraph(nodes)
            # print("Graph.subgraph(): created rx_subgraph: ", rx_subgraph.node_indices())
            new_subgraph = self.from_rustworkx(rx_subgraph)

            # frm: Create the map from subgraph node_id to parent graph node_id
            parent_node_id_map = {}
            for subgraph_node_id in new_subgraph.node_indices:
                parent_node_id_map[subgraph_node_id] = new_subgraph.get_node_data_dict(subgraph_node_id)["parent_node_id"]

            # print("Graph.subgraph(): new RX subgraph type is: ", type(new_subgraph))
        else:
            raise Exception("Graph.subgraph - bad kind of graph object")

        new_subgraph.is_a_subgraph = True
        new_subgraph.parent_node_id_map = parent_node_id_map

        return new_subgraph

    def nx_generic_bfs_edges(self, source, neighbors=None, depth_limit=None):
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

    def generic_bfs_successors_generator(self, root_node_id):
        # frm: Generate in sequence a tuple for the parent (node_id) and
        #       the children of that node (list of node_ids).
        parent = root_node_id
        children = []
        for p, c in self.nx_generic_bfs_edges(root_node_id):
            # frm: parent-child pairs appear ordered by their parent, so
            #       we can collect all of the children for a node by just
            #       iterating through pairs until the parent changes.
            if p == parent:
                children.append(c)
                continue
            yield (parent, children)
            # new parent, so add the current child to list of children before looping
            children = [c]
            parent = p
        yield (parent, children)
    
    def generic_bfs_successors(self, root_node_id):
        return dict(self.generic_bfs_successors_generator(root_node_id))

    def generic_bfs_predecessors(self, root_node_id):
        predecessors = []
        for s, t in self.nx_generic_bfs_edges(root_node_id):
            predecessors.append((t,s))
        return dict(predecessors)


    def predecessors(self, root_node_id):

        # frm TODO:  RX version NYI...

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

        TODO: The code in NetworkX for bfs_successors() and bfs_predecessors()
              works on undirected graphs (with cleverness to cut cycles), but
              the same named routines in RX only operate on directed graphs,
              so there is work to be done to make this functionality work 
              for RX...
        """

        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return {a: b for a, b in networkx.bfs_predecessors(self.nxgraph, root_node_id)}
        elif (self.isRxGraph()):
            # frm TODO:  Implement this for RX - note the RX version won't work - it is for directed graphs only
            return self.generic_bfs_predecessors(root_node_id)
            raise Exception("Graph.predecessors() for RX is NYI")
        else:
            raise Exception("Graph.predecessors - bad kind of graph object")

    def successors(self, root_node_id):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return {a: b for a, b in networkx.bfs_successors(self.nxgraph, root_node_id)}
        elif (self.isRxGraph()):
            return self.generic_bfs_successors(root_node_id)
        else:
            raise Exception("Graph.successors - bad kind of graph object")

    def neighbors(self, node):
        self.verifyGraphIsValid()

        # NX  neighbors() returns a <dict_keyiterator> which iterates over the node_ids of neighbor nodes
        # RX  neighbors() returns a NodeIndices object with the list of node_ids of neighbor nodes
        # However, the code outside graph.py only ever iterates over all neighbors so returning a list works...
        if (self.isNxGraph()):
            return list(self.nxgraph.neighbors(node))
        elif (self.isRxGraph()):
            return list(self.rxgraph.neighbors(node))
        else:
            raise Exception("Graph.neighbors - bad kind of graph object")

    def degree(self, node: Any) -> int:
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return self.nxgraph.degree(node)
        elif (self.isRxGraph()):
            return self.rxgraph.degree(node)
        else:
            raise Exception("Graph.degree - bad kind of graph object")

    def get_node_data_dict(self, node_id):
        # This routine returns the data dictionary for the given node's data

        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            data_dict = self.nxgraph.nodes[node_id]
        elif (self.isRxGraph()):
            data_dict = self.rxgraph[node_id]
        else:
            raise Exception("Graph.get_node_data_dict - bad kind of graph object")

        if not isinstance(data_dict, dict):
            raise Exception("node data is not a dictionary");
        
        return data_dict

    def get_edge_data_dict(self, edge_id):
        # This routine returns the data dictionary for the given edge's data

        """
        CLEVERNESS ALERT!
        
        The type of the edge_id parameter will be a tuple in the case of an 
        embedded NX graph but will be an integer in the case of an RX embedded
        graph.
        
        """

        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            data_dict = self.nxgraph.edges[edge_id]
        elif (self.isRxGraph()):
            data_dict = self.rxgraph.edges()[edge_id]
        else:
            raise Exception("Graph.get_node_data_dict - bad kind of graph object")

        if not isinstance(data_dict, dict):
            raise Exception("node data is not a dictionary");
        
        return data_dict
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
        import geopandas as gp

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

        # Store CRS data as an attribute of the NX graph
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

        if left_index is not None:
            ids_to_index = networkx.get_node_attributes(self, left_index)
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

def add_boundary_perimeters(graph: Graph, geometries: pd.Series) -> None:
    """
    Add shared perimeter between nodes and the total geometry boundary.

    :param graph: NetworkX graph
    :type graph: :class:`Graph`
    :param geometries: :class:`geopandas.GeoSeries` containing geometry information.
    :type geometries: :class:`pandas.Series`

    :returns: The updated graph.
    :rtype: Graph
    """
    from shapely.ops import unary_union
    from shapely.prepared import prep

    prepared_boundary = prep(unary_union(geometries).boundary)

    boundary_nodes = geometries.boundary.apply(prepared_boundary.intersects)

    for node in graph:
        graph.nodes[node]["boundary_node"] = bool(boundary_nodes[node])
        if boundary_nodes[node]:
            total_perimeter = geometries[node].boundary.length
            shared_perimeter = sum(
                neighbor_data["shared_perim"] for neighbor_data in graph[node].values()
            )
            boundary_perimeter = total_perimeter - shared_perimeter
            graph.nodes[node]["boundary_perim"] = boundary_perimeter


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
        return tuple(self.graph.neighbors(n))

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
        return self.get_node_data_dict(node)[field]

    def subgraph(self, nodes: Iterable[Any]) -> "FrozenGraph":
        return FrozenGraph(self.graph.subgraph(nodes))
