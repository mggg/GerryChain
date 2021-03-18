import json

import geopandas
import networkx
import numpy
import math

from ..updaters import compute_edge_flows, flows_from_changes, cut_edges
from .assignment import get_assignment
from .subgraphs import SubgraphView


class Partition:
    """
    Partition represents a partition of the nodes of the graph. It will perform
    the first layer of computations at each step in the Markov chain - basic
    aggregations and calculations that we want to optimize.

    :ivar gerrychain.Graph graph: The underlying graph.
    :ivar gerrychain.Assignment assignment: Maps node IDs to district IDs.
    :ivar dict parts: Maps district IDs to the set of nodes in that district.
    :ivar dict subgraphs: Maps district IDs to the induced subgraph of that district.
    """

    default_updaters = {"cut_edges": cut_edges}

    def __init__(
        self, graph=None, assignment=None, updaters=None, parent=None, flips=None
    ):
        """
        :param graph: Underlying graph.
        :param assignment: Dictionary assigning nodes to districts.
        :param updaters: Dictionary of functions to track data about the partition.
            The keys are stored as attributes on the partition class,
            which the functions compute.
        """
        if parent is None:
            self._first_time(graph, assignment, updaters)
        else:
            self._from_parent(parent, flips)

        self._cache = dict()
        self.subgraphs = SubgraphView(self.graph, self.parts)

    def _first_time(self, graph, assignment, updaters):
        self.graph = graph

        self.assignment = get_assignment(assignment, graph)

        if set(self.assignment) != set(graph):
            raise KeyError("The graph's node labels do not match the Assignment's keys")

        if updaters is None:
            updaters = dict()

        self.updaters = self.default_updaters.copy()
        self.updaters.update(updaters)

        self.parent = None
        self.flips = None
        self.flows = None
        self.edge_flows = None

    def _from_parent(self, parent, flips):
        self.parent = parent
        self.flips = flips

        self.assignment = parent.assignment.copy()
        self.assignment.update(flips)

        self.graph = parent.graph
        self.updaters = parent.updaters

        self.flows = flows_from_changes(parent.assignment, flips)
        self.edge_flows = compute_edge_flows(self)

    def __repr__(self):
        number_of_parts = len(self)
        s = "s" if number_of_parts > 1 else ""
        return "<{} [{} part{}]>".format(self.__class__.__name__, number_of_parts, s)

    def __len__(self):
        return len(self.parts)

    def flip(self, flips):
        """Returns the new partition obtained by performing the given `flips`
        on this partition.

        :param flips: dictionary assigning nodes of the graph to their new districts
        :return: the new :class:`Partition`
        :rtype: Partition
        """
        return self.__class__(parent=self, flips=flips)

    def crosses_parts(self, edge):
        """Answers the question "Does this edge cross from one part of the
        partition to another?

        :param edge: tuple of node IDs
        :rtype: bool
        """
        return self.assignment[edge[0]] != self.assignment[edge[1]]

    def __getitem__(self, key):
        """Allows accessing the values of updaters computed for this
        Partition instance.

        :param key: Property to access.
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
        """Plot the partition, using the provided geometries.

        :param geometries: A :class:`geopandas.GeoDataFrame` or :class:`geopandas.GeoSeries`
            holding the geometries to use for plotting. Its :class:`~pandas.Index` should match
            the node labels of the partition's underlying :class:`~gerrychain.Graph`.
        :param `**kwargs`: Additional arguments to pass to :meth:`geopandas.GeoDataFrame.plot`
            to adjust the plot.
        """
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

    def get_num_spanning_trees(self, district):
        '''
        Given a district number, returns the number of spanning trees in the
        subgraph of self corresponding to the district.
        Uses Kirchoff's theorem to compute the number of spanning trees.

        :param self: :class:`gerrychain.Partition`
        :param district: A district in self
        :return: The number of spanning trees in the subgraph of self
        corresponding to district
        '''
        graph = self.subgraphs[district]
        laplacian = networkx.laplacian_matrix(graph)
        L = numpy.delete(numpy.delete(laplacian.todense(), 0, 0), 1, 1)
        return math.exp(numpy.linalg.slogdet(L)[1])

    @classmethod
    def from_districtr_file(cls, graph, districtr_file, updaters=None):
        """Create a Partition from a districting plan created with `Districtr`_,
        a free and open-source web app created by MGGG for drawing districts.

        The provided ``graph`` should be created from the same shapefile as the
        Districtr module used to draw the districting plan. These shapefiles may
        be found in a repository in the `mggg-states`_ GitHub organization, or by
        request from MGGG.

        .. _`Districtr`: https://mggg.org/Districtr
        .. _`mggg-states`: https://github.com/mggg-states

        :param graph: :class:`~gerrychain.Graph`
        :param districtr_file: the path to the ``.json`` file exported from Districtr
        :param updaters: dictionary of updaters
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
