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

# frm TODO: Documentation:     Add documentation about how this all works.  For instance,
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

        total_pop = sum(graph.node_data(n)[pop_col] for n in graph)
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

        # Note that we automatically convert NetworkX based graphs to use RustworkX
        # when we create a Partition object.
        #
        # Creating and manipulating NX Graphs is easy and users
        # are familiar with doing so.  It makes sense to preserve the use case of 
        # creating an NX-Graph and then allowing the code to under-the-covers
        # convert to RX - both for legacy compatibility, but also because NX provides
        # a really nice and easy way to create graphs.
        #
        # TODO: Documentation: update the documentation
        # to describe the use case of creating a graph using NX.  That documentation
        # should also describe how to post-process results of a MarkovChain run
        # but I haven't figured that out yet...

        # If a NX.Graph, create a Graph object based on NX
        if isinstance(graph, networkx.Graph):
            graph = Graph.from_networkx(graph)

        # if a Graph object, make sure it is based on an embedded RustworkX.PyGraph
        if isinstance(graph, Graph):
            # frm: TODO: Performance: Remove this short-term hack to do performance testing
            #
            # This "test_performance_using_NX_graph" hack just forces the partition
            # to NOT convert the NX graph to be RX based.  This allows me to 
            # compare RX performance to NX performance with the same code - so that
            # whatever is different is crystal clear.
            test_performance_using_NX_graph = False
            if (graph.is_nx_graph()) and test_performance_using_NX_graph:
                self.assignment = get_assignment(assignment, graph)
                print("=====================================================")
                print("Performance-Test: using NetworkX for Partition object")
                print("=====================================================")

            elif (graph.is_nx_graph()):

                # Get the assignment that would be appropriate for the NX-based graph
                old_nx_assignment = get_assignment(assignment, graph)

                # Convert the NX graph to be an RX graph
                graph = graph.convert_from_nx_to_rx()

                # After converting from NX to RX, we need to update the Partition's assignment
                # because it used the old NX node_ids (converting to RX changes node_ids)
                nx_to_rx_node_id_map = graph.get_nx_to_rx_node_id_map()
                new_rx_assignment = old_nx_assignment.new_assignment_convert_old_node_ids_to_new_node_ids(
                  nx_to_rx_node_id_map
                )
                self.assignment = new_rx_assignment

            else:
                self.assignment = get_assignment(assignment, graph)

            self.graph = FrozenGraph(graph)

        elif isinstance(graph, FrozenGraph):
            # frm: TODO: Verify that the embedded graph is RX
            self.graph = graph
            self.assignment = get_assignment(assignment, graph)

        else:
            raise TypeError(f"Unsupported Graph object with type {type(graph)}")

        if set(self.assignment) != set(graph):
            raise KeyError("The graph's node labels do not match the Assignment's keys")

        if updaters is None:
            updaters = dict()

        if use_default_updaters:
            self.updaters = self.default_updaters
        else:
            self.updaters = {}

        self.updaters.update(updaters)

        # Note that the updater functions are executed lazily - that is, only when
        # a caller asks for the results, such as partition["perimeter"].  See the code
        # for __getitem__().
        #
        # So no need to execute the updater functions now...

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

    def flip(self, flips: Dict, use_original_nx_node_ids=False) -> "Partition":
        """
        Returns the new partition obtained by performing the given `flips`
        on this partition.

        :param flips: dictionary assigning nodes of the graph to their new districts
        :returns: the new :class:`Partition`
        :rtype: Partition
        """

        # frm: TODO: Documentation: Change comments above to document new optional parameter, use_original_nx_node_ids.
        #
        # This is a new issue that arises from the fact that node_ids in RX are different from those
        # in the original NX graph.  In the pre-RX code, we did not need to distinguish between
        # calls to flip() that were internal code used when doing a MarkovChain versus user code
        # for instance in tests.  However, in the new RX world, the internal code uses RX node_ids
        # and the tests want to use "original" NX node_ids.  Hence the new parameter.

        # If the caller identified flips in terms of "original" node_ids (typically node_ids associated with 
        # an NX-based graph before creating a Partition object), then translate those original node_ids 
        # into the appropriate internal RX-based node_ids.
        # 
        # Note that original node_ids in flips are typically used in tests
        #

        if use_original_nx_node_ids:
            new_flips = {}
            for original_nx_node_id, part in flips.items():
                internal_node_id = self.graph.internal_node_id_for_original_nx_node_id(original_nx_node_id)
                new_flips[internal_node_id] = part
            flips = new_flips

        return self.__class__(parent=self, flips=flips)

    def crosses_parts(self, edge: Tuple) -> bool:
        """
        :param edge: tuple of node IDs
        :type edge: Tuple

        :returns: True if the edge crosses from one part of the partition to another
        :rtype: bool
        """
        return self.assignment.mapping[edge[0]] != self.assignment.mapping[edge[1]]

    def __getitem__(self, key: str) -> Any:
        """
        Allows accessing the values of updaters computed for this
        Partition instance.

        :param key: Property to access.
        :type key: str

        :returns: The value of the updater.
        :rtype: Any
        """
        # frm: Cleverness Alert:  Delayed evaluation of updater functions...
        #                           
        #   The code immediately below executes the appropriate updater function
        #   if it has not already been executed and then caches the results.
        #   This makes sense - why compute something if nobody ever wants it,
        #   but it took me a while to figure out why the constructor did not
        #   explicitly call the updaters.
        #

        if key not in self._cache:
            # frm: TODO:  Add code to check that the desired updater actually is
            #               defined in the list of updaters.  If not, then this 
            #               would produce a perhaps difficult to debug problem...
            self._cache[key] = self.updaters[key](self)
        return self._cache[key]

    def __getattr__(self, key):
        # frm TODO:  Not sure it makes sense to allow two ways to accomplish the same thing...
        #
        # The code below allows Partition users to get the results of updaters by just 
        # doing:  partition.<updater_name>  which is the same as doing: partition["<updater_name>"]
        # It is clever, but perhaps too clever.  Why provide two ways to do the same thing?
        #
        # It is also odd on a more general level - this approach means that the attributes of a
        # Partition are the same as the names of the updaters and return the results of running
        # the updater functions.  I guess this makes sense, but there is no documentation (that I
        # am aware of) that makes this clear.
        #
        # Peter's comment in PR:
        #
        # This is actually on my list of things that I would prefer removed. When I first 
        # started working with this codebase, I found the fact that you could just do 
        # partition.name_of_my_updater really confusing, and, from a Python perspective, 
        # I think that the more intuitive interface is keyword access like in a dictionary. 
        # I haven't scoured the codebase for instances of ".attr" yet, but this is one of 
        # the things that I am 100% okay with getting rid of. Almost all of the people 
        # that I have seen work with this package use the partition["attr"] paradigm anyway.
        #
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
            if hasattr(self.graph, "geometry"):
                geometries = self.graph.geometry
            else:
                raise Exception("Partition.plot: graph has no geometry data")

        if set(geometries.index) != self.graph.node_indices:
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
            node_to_id = {node: str(graph.node_data(node)[id_column_key]) for node in graph}
        except KeyError:
            raise TypeError(
                "The provided graph is missing the {} column, which is "
                "needed to match the Districtr assignment to the nodes of the graph."
            )

        # frm: TODO:  NX vs. RX issues:  does "node in graph" work for both NX and RX?
        assignment = {node: districtr_assignment[node_to_id[node]] for node in graph}

        return cls(graph, assignment, updaters)
