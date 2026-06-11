from __future__ import annotations

import json
from collections.abc import Callable, KeysView
from typing import Any

# frm:  Only used in _first_time() inside __init__() to allow for creating
#       a Partition from a NetworkX Graph object:
#
#           elif isinstance(graph, networkx.Graph):
#               graph = Graph.from_networkx(graph)
#               self.graph = FrozenGraph(graph)
import networkx

from gerrychain.graph.graph import FrozenGraph, Graph

from ..updaters import compute_edge_flows, cut_edges, flows_from_changes
from .assignment import Assignment, get_assignment
from .initial_partition_generators import recursive_tree_part
from .subgraphs import SubgraphView


class Partition:
    """
    The Partition class represents a partition of the nodes of the
    graph into districts (parts).  Every iteration of MarkovChain
    creates a new Partition object from the previous Partition object
    by performing the set of flips (changes in association of a node
    to a district (perhaps confusingly called a "part").

    Perhaps the primary class attribute is "assignment" which
    stores the set of nodes in each district ("part").

    Note that the "parts" class attribute is actually a function
    that returns the "parts" of the assignment class attribute.

    A Partition object also provides access (via __getitem__()) to
    the values computed by updater functions (see comment on updaters
    in the file updaters/flows.py).

    Note that by default the constructor for a Partition object will
    convert the underlying graph in a Graph object from NetworkX to
    RustworkX - because RustworkX is so much faster than NetworkX.
    This is done in the _first_time() function below.

    It is perhaps worth noting that when we convert the underlying
    graph object from NX to RX, we create a mapping dict
    that records the "original" NX node_ids and the new RX
    node_ids.  It is stored as a class attribute of the
    new Graph object: Graph.nx_to_rx_node_id_map.  We use this
    mapping to update the "assignment" class to use the new
    RX node_ids.

    Lastly the "subgraphs" class attribute stores a subgraph for each
    district ("part").  Note that this is done for efficiency reasons
    because creating a subgraph is expensive - so subgraphs are created
    lazily (on demand) and subsequently cached.

    Attributes:
        graph (Graph): The underlying graph.
        assignment (Assignment): Maps node IDs to district IDs.
        parts (Dict): Maps district IDs to the set of nodes in that district.
        subgraphs (Dict): Maps district IDs to the induced subgraph of that district.
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
        graph: Graph | FrozenGraph | networkx.Graph | None = None,
        assignment: dict | Assignment | str | None = None,
        updaters: dict[str, Callable] | None = None,
        parent: Partition | None = None,
        flips: dict | None = None,
        use_default_updaters: bool = True,
    ) -> None:
        """Initialize a Partition instance.

        Args:
            graph (Any): Underlying graph.
            assignment (Any): Dictionary assigning nodes to districts.
            updaters (Any): Dictionary of functions to track data about the partition. The keys are
                stored as attributes on the partition class, which the functions compute.
            use_default_updaters (Any): If `False`, do not include default updaters.
        """

        if parent is None:
            if graph is None:
                raise Exception("Parition.__init__(): graph object is None")

            self._first_time(graph, assignment, updaters, use_default_updaters)
        else:
            self._from_parent(parent, flips)

        self._cache = dict()

        # SubgraphView provides cached access to subgraphs for each of the
        # partition's districts.  It is important that we asign subgraphs AFTER
        # we have established what nodes belong to which parts (districts).  In
        # the case when the parent is None, the assignments are explicitly provided,
        # and in the case when there is a parent, the _from_parent() logic processes
        # the flips to update the assignments.

        self.subgraphs = SubgraphView(self.graph, self.parts)

    @classmethod
    def from_random_assignment(
        cls,
        graph: Graph,
        n_parts: int,
        epsilon: float,
        pop_col: str,
        updaters: dict[str, Callable] | None = None,
        use_default_updaters: bool = True,
        method: Callable = recursive_tree_part,
    ) -> Partition:
        """Create a Partition with a random assignment of nodes to districts.

        This method creates a Partition with a random assignment of nodes to districts. It returns
        partition created with a random assignment.

        Args:
            graph (Graph): The graph to create the Partition from.
            n_parts (int): The number of districts to divide the nodes into.
            epsilon (float): The maximum relative population deviation from the ideal
            pop_col (str): The column of the graph's node data that holds the population data.
            updaters (Optional[Dict[str, Callable]], optional): Dictionary of updaters
            use_default_updaters (bool, optional): If `False`, do not include default updaters.
            method (Callable, optional): The function to use to partition the graph into
                ``n_parts``. Defaults to `gerrychain.tree.recursive_tree_part`.

        Returns:
            Partition: The partition created with a random assignment
        """

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

    def _first_time(
        self,
        graph: Graph | FrozenGraph | networkx.Graph,
        assignment: dict | Assignment | str | None,
        updaters: dict[str, Callable] | None,
        use_default_updaters: bool,
    ) -> None:
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

        # If a NX.Graph, create a Graph object based on NX
        if isinstance(graph, networkx.Graph):
            graph = Graph.from_networkx(graph)

        # if a Graph object, make sure it is based on an embedded RustworkX.PyGraph
        if isinstance(graph, Graph):
            # Performance Testing:  In order to compare the performance of
            # RustworkX vs NetworkX, we enable using an NX-based Graph in a partition
            # by setting the variable, test_performance_using_NX_graph, to be True.
            # This allows us to run a test with NX and then again with RX in order
            # to compare the results.
            #
            # RustworkX is much faster, so the default value is False.
            #
            # Peter said (January 2026): It might be worth changing this to a global
            # variable that we can set easily. I'll want to remove it once we get
            # to release 2.0.0, but it could be useful in the meantime..
            #
            test_performance_using_NX_graph = False

            if (graph.is_nx_graph()) and test_performance_using_NX_graph:
                self.assignment = get_assignment(assignment, graph)
                print("=====================================================")
                print("Performance-Test: using NetworkX for Partition object")
                print("=====================================================")

            elif graph.is_nx_graph():
                # Get the assignment that would be appropriate for the NX-based graph
                old_nx_assignment = get_assignment(assignment, graph)

                # Convert the NX graph to be an RX graph
                graph = graph.convert_from_nx_to_rx()

                # After converting from NX to RX, we need to update the Partition's assignment
                # because it used the old NX node_ids (converting to RX changes node_ids)
                nx_to_rx_node_id_map = graph.get_nx_to_rx_node_id_map()
                rx_assign = old_nx_assignment.new_assignment_convert_old_node_ids_to_new_node_ids(
                    nx_to_rx_node_id_map
                )
                self.assignment = rx_assign

            else:
                self.assignment = get_assignment(assignment, graph)

            self.graph = FrozenGraph(graph)

        elif isinstance(graph, FrozenGraph):
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

    def _from_parent(self, parent: Partition, flips: dict) -> None:
        self.parent = parent
        self.flips = flips

        self.graph = parent.graph
        self.updaters = parent.updaters

        self.flows = flows_from_changes(parent, self)  # careful

        self.assignment = parent.assignment.copy()
        self.assignment.update_flows(self.flows)

        if "cut_edges" in self.updaters:
            self.edge_flows = compute_edge_flows(self)

    def __repr__(self) -> str:
        number_of_parts = len(self)
        s = "s" if number_of_parts > 1 else ""
        return f"<{self.__class__.__name__} [{number_of_parts} part{s}]>"

    def __len__(self) -> int:
        return len(self.parts)

    def flip(
        self, flips: dict, flips_passed_in_use_original_nx_node_ids: bool = False
    ) -> Partition:
        """Returns the new partition obtained by performing the given `flips` on this partition.

        This method returns the new partition obtained by performing the given `flips` on this
        partition. It returns new Partition.

        Args:
            flips (Dict): dictionary assigning nodes of the graph to their new districts
            flips_passed_in_use_original_nx_node_ids (bool): Denotes whether the node_ids in the
                flips are original NX node_ids or whether they are internal RX node_ids. The only
                time this is set to True is for testing when the test wants to provide explicit
                flips using NX node_ids (because the test cannot know what node_ids RX will choose
                when we convert the underlying graph object).

        Returns:
            Partition: the new Partition
        """

        if flips_passed_in_use_original_nx_node_ids:
            new_flips = {}
            for original_nx_node_id, part in flips.items():
                internal_node_id = self.graph.internal_node_id_for_original_nx_node_id(
                    original_nx_node_id
                )
                new_flips[internal_node_id] = part
            flips = new_flips

        return self.__class__(parent=self, flips=flips)

    def crosses_parts(self, edge: tuple) -> bool:
        """Return True if the edge crosses from one part of the partition to another.

        This method returns True if the edge crosses from one part of the partition to another. It
        returns true if the edge crosses from one part of the partition to another.

        Args:
            edge (Tuple): tuple of node IDs

        Returns:
            bool: True if the edge crosses from one part of the partition to another
        """
        return self.assignment.mapping[edge[0]] != self.assignment.mapping[edge[1]]

    def __getitem__(self, key: str) -> Any:
        """Access the value of one of this Partition's updaters by name.

        The ``[]`` interface indexes **updaters**, not nodes: ``key`` is an updater name (e.g.
        ``"cut_edges"``), and the return value is that updater's computed result (lazily evaluated
        and cached). For the node-to-part assignment itself, use :attr:`assignment`; see
        :meth:`keys` for more on this distinction.

        Args:
            key (str): The name of the updater to access.

        Returns:
            Any: The value of the named updater.
        """
        # Cleverness Alert:  Delayed evaluation of updater functions...
        #
        # The code immediately below executes the appropriate updater function
        # if it has not already been executed and then caches the results.
        # This makes sense - why compute something if nobody ever wants it,
        # but it took me a while to figure out why the constructor did not
        # explicitly call the updaters.
        #

        if key not in self._cache:
            # frm: TODO: Testing:  Add a test checking what happens if no updater defined
            #
            # This code checks that the desired updater actually is
            # defined in the list of updaters.  If not, then this
            # would produce a perhaps difficult to debug problem...
            if key not in self.updaters:
                raise KeyError(
                    f"__getitem__(): updater: {key} not defined in the updaters for the partition"
                )

            self._cache[key] = self.updaters[key](self)
        return self._cache[key]

    def __getattr__(self, key: str) -> object:
        raise Exception(
            "The Partition object no longer supports <partition>.<updater> to "
            "access updater results.  Instead use <partition>['updater-name']"
        )

    def keys(self) -> KeysView[str]:
        """Return the names of this partition's updaters.

        Important: a Partition's mapping/``[]`` interface is over its **updaters**, not its nodes.
        So ``partition["population"]`` evaluates the ``"population"`` updater, and ``keys()``
        returns the updater names (e.g. ``["cut_edges", "population", ...]``) - not node_ids or
        part_ids. This often surprises people who think of a Partition as a node-to-district map.

        The actual node-to-part data lives in :attr:`assignment` (``partition.assignment``, a
        node_id -> part_id mapping), and the inverse part-to-nodes view is :attr:`parts`
        (``partition.parts``).

        Returns:
            KeysView[str]: A view of the updater names available on this partition.
        """
        return self.updaters.keys()

    @property
    def parts(self) -> dict:
        return self.assignment.parts

    def plot(self, geometries: object | None = None, **kwargs: object) -> object:
        #
        # frm ???:  I think that this plots districts on a map that is defined
        #           by the geometries parameter (presumably polygons or something similar).
        #           It converts the partition data into data that the plot routine
        #           knows how to deal with, but essentially it just assigns each node
        #           to a district.  the **kwargs are then passed to the plotting
        #           engine - presumably to define colors and other graph stuff.
        #

        """Plot the partition, using the provided geometries.

        This method plots the partition, using the provided geometries. It returns matplotlib axes
        object. Which plots the Partition.

        Args:
            geometries (geopandas.GeoDataFrame or geopandas.GeoSeries): A
                GeoDataFrame or GeoSeries holding the
                geometries to use for plotting. Its Index should match the node
                labels of the partition's underlying Graph.
            `**kwargs` (Any): Additional arguments to pass to `geopandas.GeoDataFrame.plot`
                to adjust the plot.

        Returns:
            matplotlib.axes.Axes: The matplotlib axes object. Which plots the Partition.
        """
        import geopandas

        if geometries is None:
            if hasattr(self.graph, "geometry"):
                geometries = self.graph.geometry
            else:
                raise Exception("Partition.plot: graph has no geometry data")

        if set(geometries.index) != self.graph.node_indices:
            raise TypeError("The provided geometries do not match the nodes of the graph.")
        assignment_series = self.assignment.to_series()
        if isinstance(geometries, geopandas.GeoDataFrame):
            geometries = geometries.geometry
        df = geopandas.GeoDataFrame({"assignment": assignment_series}, geometry=geometries)
        return df.plot(column="assignment", **kwargs)

    @classmethod
    def from_districtr_file(
        cls,
        graph: Graph,
        districtr_file: str,
        updaters: dict[str, Callable] | None = None,
    ) -> Partition:
        """Return partition created from the Districtr file.

        Create a Partition from a districting plan created with `Districtr`_, a free and
        open-source web app created by MGGG for drawing districts.

        The provided ``graph`` should be created from the same shapefile as the Districtr module
        used to draw the districting plan. These shapefiles may be found in a repository in the
        `mggg-states`_ GitHub organization, or by request from MGGG.

        .. _`Districtr`: https://mggg.org/Districtr .. _`mggg-states`:
        https://github.com/mggg-states

        Args:
            graph (Graph): The graph to create the Partition from
            districtr_file (str): the path to the ``.json`` file exported from Districtr
            updaters (Optional[Dict[str, Callable]], optional): dictionary of updaters

        Returns:
            Partition: The partition created from the Districtr file
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

        # frm: TODO: Testing: Verify that there is a test for from_districtr_file()

        assignment = {
            node_id: districtr_assignment[node_to_id[node_id]] for node_id in graph.node_indices
        }

        return cls(graph, assignment, updaters)
