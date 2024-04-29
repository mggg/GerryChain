import json
import networkx

from gerrychain.graph.graph import FrozenGraph, Graph
from ..updaters import compute_edge_flows, flows_from_changes, cut_edges
from .assignment import get_assignment
from .subgraphs import SubgraphView
from ..tree import recursive_tree_part
from typing import Any, Callable, Dict, Optional, Tuple


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
            self._first_time(graph, assignment, updaters, use_default_updaters)
        else:
            self._from_parent(parent, flips)

        self._cache = dict()
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
        total_pop = sum(graph.nodes[n][pop_col] for n in graph)
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
        if isinstance(graph, Graph):
            self.graph = FrozenGraph(graph)
        elif isinstance(graph, networkx.Graph):
            graph = Graph.from_networkx(graph)
            self.graph = FrozenGraph(graph)
        elif isinstance(graph, FrozenGraph):
            self.graph = graph
        else:
            raise TypeError(f"Unsupported Graph object with type {type(graph)}")

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
            node_to_id = {node: str(graph.nodes[node][id_column_key]) for node in graph}
        except KeyError:
            raise TypeError(
                "The provided graph is missing the {} column, which is "
                "needed to match the Districtr assignment to the nodes of the graph."
            )

        assignment = {node: districtr_assignment[node_to_id[node]] for node in graph}

        return cls(graph, assignment, updaters)
