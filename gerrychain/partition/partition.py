"""The :class:`Partition` - an assignment of graph nodes to districts, plus cached updaters.

A :class:`Partition` is GerryChain's central data structure. It represents a single districting
plan: an assignment of every node of a :class:`~gerrychain.Graph` to a *part* - one district of the
plan. (In code these are called *parts*, short for "part of a partition".) It also carries a set
of *updaters* - named functions that compute derived quantities about the plan (cut edges, district
populations, perimeters, election results, ...) on demand.

A Partition is also the *state* of GerryChain's Markov chain. Each step of a chain takes the current
Partition and produces a new child Partition that differs by only a small set of node reassignments
("flips"); see :meth:`Partition.flip` and the ``parent`` attribute. Most of the design of this class
is shaped by that use case, so the following choices are worth understanding.

Assignment vs. parts (why keep both?):
    The same plan can be viewed two ways, and different code wants different views:

    * ``assignment`` (an :class:`~gerrychain.partition.assignment.Assignment`) is the
      node -> part map. It is the source of truth and is cheap to update flip-by-flip.
    * ``parts`` is the inverse, part -> set-of-nodes, view. Many updaters and the recombination
      proposals need to iterate the nodes of a part, for which the inverse view is far more
      convenient and efficient than scanning the entire assignment.

    Keeping both means neither direction of lookup has to be recomputed from the other on every use;
    the ``Assignment`` object keeps the two consistent as flips are applied.

Tracking changes (flips and flows):
    Each child Partition records the ``flips`` that produced it (the nodes whose part differs from
    the parent) and derives from them the node and edge *flows*: the per-part sets of nodes and
    edges that entered or left. Those flows are what let the incremental updaters patch the parent's
    cached values instead of recomputing from scratch. See :mod:`gerrychain.updaters.flows`.

FrozenGraph:
    The underlying graph does not change over the course of a chain - only the assignment of nodes
    to districts does. The graph is therefore wrapped in a
    :class:`~gerrychain.graph.graph.FrozenGraph`, an immutable view created once and shared by every
    Partition in the chain. Freezing the graph buys two things:

    * it lets per-graph results be cached safely (e.g. ``FrozenGraph.neighbors`` /
      ``FrozenGraph.degree`` are memoized), since the graph can never change under the cache; and
    * it removes a class of cache-invalidation bugs that a shared, mutable graph could cause if it
      were edited mid-chain.

    The expensive operations a Partition tries to avoid or amortize are: converting a NetworkX graph
    to RustworkX, constructing per-district subgraphs (done lazily and cached via ``SubgraphView``),
    and recomputing updaters.

Updaters:
    Updater values are computed lazily and cached the first time they are requested via
    ``partition[name]`` (see :meth:`__getitem__`). Many updaters are additionally *incremental*
    meaning that they start from the parent partition's cached value and patch only what changed,
    using the node/edge "flows" between parent and child. See :mod:`gerrychain.updaters.flows`.

Inside vs. outside a Markov chain:
    A Partition is most useful as chain state, but it is also handy for post-hoc analysis of a fixed
    plan (computing its cut edges, population deviation, partisan metrics, etc.). The distinguishing
    feature is the ``parent``: a chain produces a lineage of partitions, each with a parent, which
    is exactly what the incremental/flow updaters exploit. A standalone Partition built directly
    from a graph and an assignment has ``parent is None``; its flow-based updaters then simply fall
    back to computing everything from scratch (their "initializer" path). The same updaters
    therefore work in both settings.

Node ids inside a chain (RustworkX vs. NetworkX labels):
    When a Graph is converted to RustworkX to run a chain, its nodes are relabeled with contiguous
    internal integer ids, and a Partition's ``assignment`` is keyed by those *internal* ids, not the
    original NetworkX node labels. Code that inspects a post-chain assignment, or maps chain results
    back onto the original graph or its geometry, must therefore translate the ids back. The Graph
    carries that mapping: see :meth:`Graph.original_nx_node_id_for_internal_node_id` (and the
    set/list helpers :meth:`Graph.original_nx_node_ids_for_set` /
    :meth:`Graph.original_nx_node_ids_for_list`), and the inverse
    :meth:`Graph.internal_node_id_for_original_nx_node_id`.

Note that the mapping / ``[]`` interface of a Partition is over its *updaters*
(``partition["cut_edges"]``), not its nodes; the node -> part data lives in
``partition.assignment``. See :meth:`keys`.
"""

from __future__ import annotations

import json
import os
import random
from collections.abc import Callable, Hashable, KeysView, Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

# frm:  Only used in _first_time() inside __init__() to allow for creating
#       a Partition from a NetworkX Graph object:
#
#           elif isinstance(graph, networkx.Graph):
#               graph = Graph.from_networkx(graph)
#               self.graph = FrozenGraph(graph)
import geopandas
import networkx
import numpy

from gerrychain.graph.graph import FrozenGraph, Graph

from .._rng import make_rng
from ..updaters import compute_edge_flows, cut_edges, flows_from_changes
from .assignment import Assignment, get_assignment
from .initial_partition_generators import PartitionFn, recursive_tree_part
from .subgraphs import SubgraphView

if TYPE_CHECKING:
    import matplotlib.axes

NodeT = TypeVar("NodeT", bound=Hashable)
PartT = TypeVar("PartT", bound=Hashable)


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
        parts (dict[Hashable, frozenset[Hashable]]): Maps district IDs to the set of nodes in that
            district.
        subgraphs (SubgraphView): Maps district IDs to the induced subgraph of that district.
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
        "_assignment_vector",
    )

    graph: FrozenGraph
    assignment: Assignment
    updaters: dict[str, Callable[[Partition], Any]]
    parent: Partition | None
    flips: dict[Hashable, Hashable] | None
    flows: dict[Hashable, dict[str, set[Hashable]]] | None
    edge_flows: dict[Hashable, dict[str, set[tuple[int, int]]]] | None
    _cache: dict[str, Any]
    _assignment_vector: numpy.ndarray | None

    default_updaters: dict[str, Callable[[Partition], Any]] = {"cut_edges": cut_edges}

    def __init__(
        self,
        graph: Graph
        | FrozenGraph
        | networkx.Graph[NodeT, dict[str, Any], dict[str, Any]]
        | None = None,
        assignment: Mapping[NodeT, PartT] | Assignment | str | None = None,
        updaters: Mapping[str, Callable[[Partition], Any]] | None = None,
        parent: Partition | None = None,
        flips: Mapping[NodeT, PartT] | None = None,
        use_default_updaters: bool = True,
    ) -> None:
        """Initialize a Partition instance.

        Args:
            graph (Graph | FrozenGraph | networkx.Graph | None, optional): Underlying graph.
                Required for a root partition. Defaults to ``None``.
            assignment (Mapping[Hashable, Hashable] | Assignment | str | None, optional): Node to
                district assignment, or a node attribute containing it. Defaults to ``None``.
            updaters (Mapping[str, Callable[[Partition], Any]] | None, optional): Named updater
                functions. Their result types vary by updater. Defaults to ``None``.
            parent (Partition | None, optional): Parent partition for a child. Defaults to
                ``None``.
            flips (Mapping[Hashable, Hashable] | None, optional): Reassignments relative to the
                parent. Defaults to ``None``.
            use_default_updaters (bool, optional): Whether to include default updaters. Defaults
                to ``True``.
        """

        if parent is None:
            if graph is None:
                raise Exception("Parition.__init__(): graph object is None")

            self._first_time(graph, assignment, updaters, use_default_updaters)
        else:
            if flips is None:
                raise TypeError("A child partition requires flips")
            self._from_parent(parent, flips)

        self._cache = {}
        self._assignment_vector = None

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
        updaters: Mapping[str, Callable[[Partition], Any]] | None = None,
        use_default_updaters: bool = True,
        partition_fn: PartitionFn = recursive_tree_part,
        *,
        rng: random.Random | int | None = None,
    ) -> Partition:
        """Create a Partition with a random assignment of nodes to districts.

        This method creates a Partition with a random assignment of nodes to districts. It returns
        partition created with a random assignment.

        Args:
            graph (Graph): The graph to create the Partition from.
            n_parts (int): The number of districts to divide the nodes into.
            epsilon (float): The maximum relative population deviation from the ideal
            pop_col (str): The column of the graph's node data that holds the population data.
            updaters (Mapping[str, Callable] | None, optional): Dictionary of updaters.
            use_default_updaters (bool, optional): If `False`, do not include default updaters.
            partition_fn (PartitionFn, optional): The function to use to partition the graph into
                ``n_parts``; it returns the full node-to-part assignment dict. It is called with
                this method's normalized ``rng``, which takes precedence over an ``rng`` partially
                bound to the ``partition_fn`` parameter. Defaults to
                `gerrychain.partition.recursive_tree_part`.
            rng (random.Random | int | None, optional): Source of randomness. An integer
                creates a reproducible RNG; ``None`` creates an independent RNG from system
                entropy.

        Returns:
            Partition: The partition created with a random assignment
        """

        total_pop = sum(graph.node_data(n)[pop_col] for n in graph)
        ideal_pop = total_pop / n_parts

        assignment = partition_fn(
            graph=graph,
            parts=range(n_parts),
            pop_target=ideal_pop,
            pop_col=pop_col,
            epsilon=epsilon,
            rng=make_rng(rng),
        )

        return cls(
            graph,
            assignment,
            updaters,
            use_default_updaters=use_default_updaters,
        )

    def _first_time(
        self,
        graph: Graph | FrozenGraph | networkx.Graph[NodeT, dict[str, Any], dict[str, Any]],
        assignment: Mapping[NodeT, PartT] | Assignment | str | None,
        updaters: Mapping[str, Callable[[Partition], Any]] | None,
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

        if assignment is None:
            raise TypeError("A new partition requires an assignment")

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
            self.updaters = dict(self.default_updaters)
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

    def _from_parent(self, parent: Partition, flips: Mapping[NodeT, PartT]) -> None:
        self.parent = parent
        self.flips = {node: part for node, part in flips.items()}

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
        self,
        flips: Mapping[NodeT, PartT],
        flips_passed_in_use_original_nx_node_ids: bool = False,
    ) -> Partition:
        """Returns the new partition obtained by performing the given `flips` on this partition.

        This method returns the new partition obtained by performing the given `flips` on this
        partition. It returns new Partition.

        Args:
            flips (dict): dictionary assigning nodes of the graph to their new districts
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

    def crosses_parts(self, edge: tuple[Hashable, Hashable]) -> bool:
        """Return True if the edge crosses from one part of the partition to another.

        This method returns True if the edge crosses from one part of the partition to another. It
        returns true if the edge crosses from one part of the partition to another.

        Args:
            edge (tuple): tuple of node IDs

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
    def parts(self) -> dict[Hashable, frozenset[Hashable]]:
        return self.assignment.parts

    @property
    def assignment_vector(self) -> numpy.ndarray:
        """The part (district) label of each node, as an array indexed by internal node id.

        Computed lazily and cached. When this partition's parent has already emitted its vector,
        the child's is built by copying it and rewriting only the flipped entries, so emitting the
        vector at every step of a chain costs an array copy (C-speed) plus the handful of flips
        rather than an O(n) rebuild from the assignment mapping.

        The returned array is read-only, since child partitions build their vectors from it; call
        ``.copy()`` on it if you need a mutable version. Positions are internal node ids; use
        :meth:`Graph.original_nx_node_id_for_internal_node_id` to translate back to the original
        node labels.

        Returns:
            numpy.ndarray: Array of length ``n`` whose ``i``-th entry is the part of node ``i``.
        """
        if self._assignment_vector is None:
            parent = self.parent
            if parent is not None and parent._assignment_vector is not None and self.flips:
                vector = parent._assignment_vector.copy()
                for node, part in self.flips.items():
                    vector[cast(int, node)] = part
            else:
                vector = self.assignment.to_vector()
            vector.setflags(write=False)
            self._assignment_vector = vector
        return self._assignment_vector

    def plot(
        self,
        geometries: geopandas.GeoDataFrame | geopandas.GeoSeries | None = None,
        **kwargs: Any,
    ) -> "matplotlib.axes.Axes":
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
            **kwargs (Any): Additional arguments to pass to `geopandas.GeoDataFrame.plot`
                to adjust the plot.

        Returns:
            matplotlib.axes.Axes: The matplotlib axes object. Which plots the Partition.
        """
        if geometries is None:
            graph_geometries = getattr(self.graph, "geometry", None)
            if not isinstance(graph_geometries, (geopandas.GeoDataFrame, geopandas.GeoSeries)):
                raise Exception("Partition.plot: graph has no geometry data")
            geometries = graph_geometries

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
        districtr_file: str | os.PathLike[str],
        updaters: Mapping[str, Callable[[Partition], Any]] | None = None,
    ) -> Partition:
        """Return partition created from the Districtr file.

        Create a Partition from a districting plan created with `Districtr`_, a free and
        open-source web app created by MGGG for drawing districts.

        The provided ``graph`` should be created from the same shapefile as the Districtr module
        used to draw the districting plan. These shapefiles may be found in a repository in the
        `mggg-states`_ GitHub organization, or by request from MGGG.

        .. _`Districtr`: https://mggg.org/Districtr

        .. _`mggg-states`: https://github.com/mggg-states

        Args:
            graph (Graph): The graph to create the Partition from
            districtr_file (str | os.PathLike): the path to the ``.json`` file exported
                from Districtr
            updaters (Mapping[str, Callable] | None, optional): Dictionary of updaters.

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
