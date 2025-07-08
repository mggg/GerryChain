import json


# frm:  Only used in _first_time() inside __init__() to allow for creating
#       a Partition from a NetworkX Graph object:
#
#           elif isinstance(graph, networkx.Graph):
#               graph = Graph.from_networkx(graph)
#               self.graph = FrozenGraph(graph)
import networkx     

from gerrychain.graph.graph import FrozenGraph, Graph
from ..updaters import compute_edge_flows, flows_from_changes, cut_edges
from .assignment import get_assignment
from .subgraphs import SubgraphView
from ..tree import recursive_tree_part
from typing import Any, Callable, Dict, Optional, Tuple

# frm TODO:     Add documentation about how this all works.  For instance,
#               what is computationally expensive and how does a FrozenGraph
#               help?  Why do we need both assignments and parts?  
#
#               Since a Partition is intimately tied up with how the Markov Chain
#               does its magic, it would make sense to talk about that a bit...
#
#               For instance, is there any reason to use a Partition object 
#               except in a Markov Chain?  I suppose they are useful for post
#               Markov Chain analysis - but if so, then it would be nice to 
#               know what functionality is tuned for the Markov Chain and what
#               functionality / data is tuned for post Markov Chain analysis.

class Partition:
    """
    Partition represents a partition of the nodes of the graph. It will perform
    the first layer of computations at each step in the Markov chain - basic
    aggregations and calculations that we want to optimize.

    :ivar graph: The underlying graph.
    :type graph: :class:`~gerrychain.Graph`
    :ivar assignment: Maps node IDs to district IDs.
    :type assignment: :class:`~gerrychain.assignment.Assignment`
    :ivar parts: Maps district IDs to the set of nodes in that district.
    :type parts: Dict
    :ivar subgraphs: Maps district IDs to the induced subgraph of that district.
    :type subgraphs: Dict
    """

    __slots__ = (
        "graph",
        "subgraphs",
        "assignment",
        "updaters",
        "parent",
        "flips",
        "flows",
        "edge_flows",
        "_cache",
    )

    default_updaters = {"cut_edges": cut_edges}

    def __init__(
        self,
        graph=None,
        assignment=None,
        updaters=None,
        parent=None,
        flips=None,
        use_default_updaters=True,
    ):
        """
        :param graph: Underlying graph.
        :param assignment: Dictionary assigning nodes to districts.
        :param updaters: Dictionary of functions to track data about the partition.
            The keys are stored as attributes on the partition class,
            which the functions compute.
        :param use_default_updaters: If `False`, do not include default updaters.
        """
        
        if parent is None:
            if graph is None:
                raise Exception("Parition.__init__(): graph object is None")
                
            self._first_time(graph, assignment, updaters, use_default_updaters)
        else:
            self._from_parent(parent, flips)

        self._cache = dict()
        
        #frm:   SubgraphView provides cached access to subgraphs for each of the 
        #       partition's districts.  It is important that we asign subgraphs AFTER
        #       we have established what nodes belong to which parts (districts).  In
        #       the case when the parent is None, the assignments are explicitly provided,
        #       and in the case when there is a parent, the _from_parent() logic processes
        #       the flips to update the assignments.
        self.subgraphs = SubgraphView(self.graph, self.parts)

    @classmethod
    def from_random_assignment(
        cls,
        graph: Graph,
        n_parts: int,
        epsilon: float,
        pop_col: str,
        updaters: Optional[Dict[str, Callable]] = None,
        use_default_updaters: bool = True,
        flips: Optional[Dict] = None,
        method: Callable = recursive_tree_part,
    ) -> "Partition":
        """
        Create a Partition with a random assignment of nodes to districts.

        :param graph: The graph to create the Partition from.
        :type graph: :class:`~gerrychain.Graph`
        :param n_parts: The number of districts to divide the nodes into.
        :type n_parts: int
        :param epsilon: The maximum relative population deviation from the ideal
        :type epsilon: float
            population. Should be in [0,1].
        :param pop_col: The column of the graph's node data that holds the population data.
        :type pop_col: str
        :param updaters: Dictionary of updaters
        :type updaters: Optional[Dict[str, Callable]], optional
        :param use_default_updaters: If `False`, do not include default updaters.
        :type use_default_updaters: bool, optional
        :param flips: Dictionary assigning nodes of the graph to their new districts.
        :type flips: Optional[Dict], optional
        :param method: The function to use to partition the graph into ``n_parts``. Defaults to
            :func:`~gerrychain.tree.recursive_tree_part`.
        :type method: Callable, optional

        :returns: The partition created with a random assignment
        :rtype: Partition
        """
        # frm: ???: BUG:  TODO:  The param, flips, is never used in this routine...

        # frm: original code:   total_pop = sum(graph.nodes[n][pop_col] for n in graph)
        total_pop = sum(graph.get_node_data_dict(n)[pop_col] for n in graph)
        ideal_pop = total_pop / n_parts

        assignment = method(
            graph=graph,
            parts=range(n_parts),
            pop_target=ideal_pop,
            pop_col=pop_col,
            epsilon=epsilon,
        )

        return cls(
            graph,
            assignment,
            updaters,
            use_default_updaters=use_default_updaters,
        )

    def _first_time(self, graph, assignment, updaters, use_default_updaters):
        # Make sure that the embedded graph for the Partition is based on
        # a RustworkX graph, and make sure it is also a FrozenGraph.  Both
        # of these are important for performance.

        # If a NX.Graph, create a Graph object based on NX
        if isinstance(graph, networkx.Graph):
            graph = Graph.from_networkx(graph)

        # if a Graph object, make sure it is based on an embedded RustworkX.PyGraph
        if isinstance(graph, Graph):
            if (graph.isNxGraph()):
                graph = graph.convert_from_nx_to_rx()
            self.graph = FrozenGraph(graph)
        elif isinstance(graph, FrozenGraph):
            # frm: TODO: Verify that the embedded graph is RX.n
            self.graph = graph
        else:
            raise TypeError(f"Unsupported Graph object with type {type(graph)}")

        # frm ???:  Why is the parameter below not the FrozenGraph?  
        self.assignment = get_assignment(assignment, graph)

        if set(self.assignment) != set(graph):
            raise KeyError("The graph's node labels do not match the Assignment's keys")

        if updaters is None:
            updaters = dict()

        if use_default_updaters:
            self.updaters = self.default_updaters
        else:
            self.updaters = {}

        self.updaters.update(updaters)

        self.parent = None
        self.flips = None
        self.flows = None
        self.edge_flows = None

    # frm ???:      This is only called once and it is tagged as an internal
    #               function (leading underscore).  Is there a good reason
    #               why this is not internal to the __init__() routine 
    #               where it is used?
    #
    #               That is, is there any reason why anyone might ever 
    #               call this except __init__()?

    def _from_parent(self, parent: "Partition", flips: Dict) -> None:
        self.parent = parent
        self.flips = flips

        self.graph = parent.graph
        self.updaters = parent.updaters

        # frm ???:  What are flows?
        #
        #           Flows are just a dictionary showing what nodes flowed into a
        #           partition and what nodes flowed out of that partition.
        #           This is an example of tight logical coupling between a Partition
        #           and Markov Chain logic.
        #
        #           I assume that the flows_from_changes() takes advantage of the
        #           flips setting above.  This is all quite opaque - what one would 
        #           want for comments is a description of what happens when a new
        #           partition is created from an old one.  I assume that the FrozenGraph
        #           stays frozen and is the same in all Partitions in a chain, but that 
        #           the other stuff (flows, assignment, parts) changes with each successive
        #           partition in the chain.  Is this true?  If so, why not make that clear?
        #
        self.flows = flows_from_changes(parent, self)  # careful

        self.assignment = parent.assignment.copy()
        self.assignment.update_flows(self.flows)

        if "cut_edges" in self.updaters:
            self.edge_flows = compute_edge_flows(self)

    def __repr__(self):
        number_of_parts = len(self)
        s = "s" if number_of_parts > 1 else ""
        return "<{} [{} part{}]>".format(self.__class__.__name__, number_of_parts, s)

    def __len__(self):
        return len(self.parts)

    def flip(self, flips: Dict) -> "Partition":
        """
        Returns the new partition obtained by performing the given `flips`
        on this partition.

        :param flips: dictionary assigning nodes of the graph to their new districts
        :returns: the new :class:`Partition`
        :rtype: Partition
        """
        return self.__class__(parent=self, flips=flips)

    def crosses_parts(self, edge: Tuple) -> bool:
        """
        :param edge: tuple of node IDs
        :type edge: Tuple

        :returns: True if the edge crosses from one part of the partition to another
        :rtype: bool
        """
        return self.assignment.mapping[edge[0]] != self.assignment.mapping[edge[1]]

    # frm ???:  Not quite sure what is going on with __getitem__(), __getattr__(), and
    #           keys().  This looks like it is defining dictionary style syntax for
    #           a Partition object (the Pythonic way...), but I am not sure what the 
    #           logic is and I am not sure exactly what is being returned.
    #
    #           It looks like __getattr__ just allows accessing what __getitem__() 
    #           returns but with the syntax for an attribute instead of a dict.
    #               partition[key] and partition.key would return the same thing.
    #

    def __getitem__(self, key: str) -> Any:
        """
        Allows accessing the values of updaters computed for this
        Partition instance.

        :param key: Property to access.
        :type key: str

        :returns: The value of the updater.
        :rtype: Any
        """
        if key not in self._cache:
            self._cache[key] = self.updaters[key](self)
        return self._cache[key]

    def __getattr__(self, key):
        return self[key]

    def keys(self):
        return self.updaters.keys()

    @property
    def parts(self):
        return self.assignment.parts

    def plot(self, geometries=None, **kwargs):
        # 
        # frm ???:  I think that this plots districts on a map that is defined
        #           by the geometries parameter (presumably polygons or something similar).
        #           It converts the partition data into data that the plot routine
        #           knows how to deal with, but essentially it just assigns each node
        #           to a district.  the **kwargs are then passed to the plotting 
        #           engine - presumably to define colors and other graph stuff.
        #

        """
        Plot the partition, using the provided geometries.

        :param geometries: A :class:`geopandas.GeoDataFrame` or :class:`geopandas.GeoSeries`
            holding the geometries to use for plotting. Its :class:`~pandas.Index` should match
            the node labels of the partition's underlying :class:`~gerrychain.Graph`.
        :type geometries: geopandas.GeoDataFrame or geopandas.GeoSeries
        :param `**kwargs`: Additional arguments to pass to :meth:`geopandas.GeoDataFrame.plot`
            to adjust the plot.

        :returns: The matplotlib axes object. Which plots the Partition.
        :rtype: matplotlib.axes.Axes
        """
        import geopandas

        if geometries is None:
            geometries = self.graph.geometry
            # frm: TODO: Test that self.graph.geometry is not None - but first need to grok
            #               where this is set (other than Graph.from_geodataframe())

        if set(geometries.index) != set(self.graph.nodes):
            raise TypeError(
                "The provided geometries do not match the nodes of the graph."
            )
        assignment_series = self.assignment.to_series()
        if isinstance(geometries, geopandas.GeoDataFrame):
            geometries = geometries.geometry
        df = geopandas.GeoDataFrame(
            {"assignment": assignment_series}, geometry=geometries
        )
        return df.plot(column="assignment", **kwargs)

    @classmethod
    def from_districtr_file(
        cls,
        graph: Graph,
        districtr_file: str,
        updaters: Optional[Dict[str, Callable]] = None,
    ) -> "Partition":
        """
        Create a Partition from a districting plan created with `Districtr`_,
        a free and open-source web app created by MGGG for drawing districts.

        The provided ``graph`` should be created from the same shapefile as the
        Districtr module used to draw the districting plan. These shapefiles may
        be found in a repository in the `mggg-states`_ GitHub organization, or by
        request from MGGG.

        .. _`Districtr`: https://mggg.org/Districtr
        .. _`mggg-states`: https://github.com/mggg-states

        :param graph: The graph to create the Partition from
        :type graph: :class:`~gerrychain.Graph`
        :param districtr_file: the path to the ``.json`` file exported from Districtr
        :type districtr_file: str
        :param updaters: dictionary of updaters
        :type updaters: Optional[Dict[str, Callable]], optional

        :returns: The partition created from the Districtr file
        :rtype: Partition
        """
        with open(districtr_file) as f:
            districtr_plan = json.load(f)

        id_column_key = districtr_plan["idColumn"]["key"]
        districtr_assignment = districtr_plan["assignment"]
        try:
            # frm: original code:   node_to_id = {node: str(graph.nodes[node][id_column_key]) for node in graph}
            node_to_id = {node: str(graph.get_node_data_dict(node)[id_column_key]) for node in graph}
        except KeyError:
            raise TypeError(
                "The provided graph is missing the {} column, which is "
                "needed to match the Districtr assignment to the nodes of the graph."
            )

        assignment = {node: districtr_assignment[node_to_id[node]] for node in graph}

        return cls(graph, assignment, updaters)
