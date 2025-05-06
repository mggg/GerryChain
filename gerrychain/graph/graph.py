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

    @classmethod
    def from_networkx(cls, nxgraph: networkx.Graph) -> "Graph":
        graph = cls()
        graph.nxgraph = nxgraph
        graph.rxgraph = None
        return graph
    
    @classmethod
    def from_rustworkx(cls, rxgraph: rustworkx.PyGraph) -> "Graph":
        graph = cls()   
        graph.rxgraph = rxgraph
        return graph

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

    # frm TODO: Remove this once NX dependencies have been removed from tree.py (and other places?)
    #           Actually, this may be useful if end users have code that needs to operate on
    #           an NX Graph object...
    def getNxGraph(self):
        if not self.isNxGraph():
            raise Exception("getNxGraph - graph is not an NX version of Graph")
        return self.nxgraph

    def isRxGraph(self):
        self.verifyGraphIsValid()
        return self.rxgraph is not None

    def lookup(self, node: Any, field: Any):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return self.nxgraph.nodes[node][field]
        elif (self.isRxGraph()):
            # frm TODO:
            raise Exception("Graph.lookup NYI")
        else:
            raise Exception("Graph.lookup - bad kind of graph object")
        
    @property
    def node_indices(self):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return set(self.nxgraph.nodes)
        elif (self.isRxGraph()):
            # frm TODO:
            raise Exception("Graph.node_indices NYI")
        else:
            raise Exception("Graph.node_indices - bad kind of graph object")

    @property
    def edge_indices(self):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return set(self.nxgraph.edges)
        elif (self.isRxGraph()):
            # frm TODO:
            raise Exception("Graph.edge_indices NYI")
        else:
            raise Exception("Graph.edge_indices - bad kind of graph object")

    @property
    def edges(self):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return self.nxgraph.edges
        elif (self.isRxGraph()):
            # frm TODO:
            raise Exception("Graph.edges NYI")
        else:
            raise Exception("Graph.edges - bad kind of graph object")

    def add_data():
        # frm TODO:
        raise Exception("Graph.add_data NYI")

    def join():
        # frm TODO:
        raise Exception("Graph.join NYI")

    @property
    def islands(self):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return set(node for node in self.nxgraph if self.nxgraph.degree[node] == 0)
        elif (self.isRxGraph()):
            # frm TODO:
            raise Exception("Graph.islands NYI")
        else:
            raise Exception("Graph.islands - bad kind of graph object")

    # frm TODO:   Get rid of this hack.  I added it because code in contiguity.py 
    #               called nx.is_connected() which eventually called is_directed()
    #               assuming the graph was an nxgraph.
    def is_directed(self):
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
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return len(self.nxgraph.nodes)
        elif (self.isRxGraph()):
            # frm TODO:
            return len(self.rxgraph.nodes)
        else:
            raise Exception("Graph.len - bad kind of graph object")

    def __getattr__(self, __name: str) -> Any:
        # If attribute doesn't exist on this object, try
        # its underlying graph object...
        if (self.isNxGraph()):
            return object.__getattribute__(self.nxgraph, __name)
        elif (self.isRxGraph()):
            return object.__getattribute__(self.rxgraph, __name)
        else:
            raise Exception("Graph.__getattribute__ - bad kind of graph object")

    def __getitem__(self, __name: str) -> Any:
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return self.nxgraph[__name]
        elif (self.isRxGraph()):
            # frm TODO:
            raise Exception("Graph.__getitem__() NYI for RX")
        else:
            raise Exception("Graph.__getitem__() - bad kind of graph object")

    def __iter__(self) -> Iterable[Any]:
        yield from self.node_indices

    def subgraph(self, nodes: Iterable[Any]) -> "Graph":
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            nx_subgraph = self.nxgraph.subgraph(nodes)
            return self.from_networkx(nx_subgraph)
        elif (self.isRxGraph()):
            # frm TODO:  Need to check logic below - not sure this works exactly correctly for RX...
            rx_subgraph = self.rxgraph.subgraph(nodes)
            return self.from_rustworkx(rx_subgraph)
        else:
            raise Exception("Graph.subgraph - bad kind of graph object")

    def predecessors(self, root):

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
            return {a: b for a, b in networkx.bfs_predecessors(self.nxgraph, root)}
        elif (self.isRxGraph()):
            # frm TODO:  Implement this for RX - note the RX version won't work - it is for directed graphs only
            raise Exception("Graph.predecessors() for RX is NYI")
        else:
            raise Exception("Graph.subgraph - bad kind of graph object")

    def successors(self, root):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return {a: b for a, b in networkx.bfs_successors(self.nxgraph, root)}
        elif (self.isRxGraph()):
            # frm TODO:  Implement this for RX - note the RX version won't work - it is for directed graphs only
            raise Exception("Graph.successors() for RX is NYI")
        else:
            raise Exception("Graph.subgraph - bad kind of graph object")

    def neighbors(self, node):
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return tuple(self.nxgraph.neighbors(node))
        elif (self.isRxGraph()):
            # frm TODO:  Implement this for RX 
            raise Exception("Graph.neighbors() for RX is NYI")
        else:
            raise Exception("Graph.subgraph - bad kind of graph object")

    def degree(self, node: Any) -> int:
        self.verifyGraphIsValid()

        if (self.isNxGraph()):
            return self.nxgraph.degree(node)
        elif (self.isRxGraph()):
            # frm TODO:  Implement this for RX 
            raise Exception("Graph.degree() for RX is NYI")
        else:
            raise Exception("Graph.subgraph - bad kind of graph object")

    def get_node_data_dict(self, node_id):
        # This routine returns the data dictionary for the given node's data

        # frm TODO: 
        # The idea is to add a RustworkX graph as an internal
        # data member that gets populated when the user adds
        # the NetworkX graph to a Parition.  When that happens
        # this code should be changed so that it checks to see
        # if there is a non-null rxgraph and if so to access
        # that instead.  That code will look something like:
        #
        #   if self.rxgraph is None:
        #       data_dict = self.nodes[node_id]
        #   else:
        #       data_dict = self.rxgraph.nodes()[node_id]

        data_dict = self.nodes[node_id]

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

    def __repr__(self):
        return "<Graph [{} nodes, {} edges]>".format(len(self.nodes), len(self.edges))

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
        graph.graph["crs"] = df.crs.to_json()
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

    @property
    #frm: This is clever - perhaps too clever...  I am not 100% sure
    #       that I grok it, but I think that NodeView objects someow
    #       get represented as the keys so that asking for the list
    #       of nodes gives you just the keys and not the whole deal.
    #       For instance, you can do graph.nodes[node_id]['key'] = value
    #       so a node is more than just the key, but if you create a 
    #       set from graph,nodes, you just get the keys/ids of the nodes.
    def node_indices(self):
        return set(self.nodes)

    @property
    # frm: Similar comment as above for node_indices...
    def edge_indices(self):
        return set(self.edges)

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

    @property
    def islands(self) -> Set:
        """
        :returns: The set of degree-0 nodes.
        :rtype: Set
        """
        return set(node for node in self if self.degree[node] == 0)

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

    def issue_warnings(self) -> None:
        """
        :returns: None

        :raises: UserWarning if the graph has any red flags (right now, only islands).
        """
        self.warn_for_islands()

    def get_node_data_dict(self, node_id):
        # This routine returns the data dictionary for the given node's data

        # frm TODO:  Rethink whether this routine (get_node_data_dict) needs to exist.
        #
        #            This was an early attempt to deal with RustworkX.  It dealt
        #            with the fact that the syntax for getting a node's data dict
        #            was different for NX and RX, but I have since learned that
        #            you can muck with @property and __getattr__ to deal with
        #            those kinds of syntax issues.  So, maybe we can revert to the
        #            old syntax with cleverness.
        #
        #            On the other hand, maybe this is good because it is 
        #            very clear what is going on.  Perhaps being a little less
        #            pythonic is a good thing.
        #
        #            In any event, this works, and after a conversation with Peter
        #            in the future we can either leave it or be clever and go back
        #            to the old syntax.
        #
        #            NX syntax: data_dict = self.nodes[node_id]
        #
        #            RX syntax: data_dict = self.rxgraph.nodes()[node_id]
        #
        #            Actually, I think that the cleverness may have already been
        #            done...  

        data_dict = self.nodes[node_id]

        if not isinstance(data_dict, dict):
            raise Exception("node data is not a dictionary");
        
        return data_dict

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


# frm TODO: Probably need to implement an RX version of FrozenGraph.  It should
#           not be too difficult since all that really needs to happen is to 
#           raise exceptions if user attempts to change the graph and to do
#           the LRU cacheing.  Should check to see if RustworkX has the concept
#           of a frozen graph...
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
        return self.graph.nodes[node][field]

    def subgraph(self, nodes: Iterable[Any]) -> "FrozenGraph":
        return FrozenGraph(self.graph.subgraph(nodes))
