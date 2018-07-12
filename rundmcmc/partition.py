import collections
import sys

from rundmcmc.updaters import flows_from_changes, max_edge_cuts


class Partition:
    """
    Partition represents a partition of the nodes of the graph. It will perform
    the first layer of computations at each step in the Markov chain - basic
    aggregations and calculations that we want to optimize.

    """

    def __init__(self, graph=None, assignment=None, updaters=None,
                 parent=None, flips=None):
        """
        :graph: the underlying graph (networkx.Graph)
        :assignment: dict assigning nodes to districts. Defaults to uniformly
        assigning all nodes to district 0.
        :updaters: dict from names of attributes of the Partition to the functions
        that compute those attributes.
        """
        if parent:
            self._from_parent(parent, flips)
        else:
            self._first_time(graph, assignment, updaters)

        self._update()

        self.max_edge_cuts = max_edge_cuts(self)

    def _first_time(self, graph, assignment, updaters):
        self.graph = graph
        self.assignment = assignment

        if not assignment:
            assignment = {node: 0 for node in graph.nodes}

        if not updaters:
            updaters = dict()

        self.updaters = updaters

        self.parent = None
        self.flips = None

        self.max_edge_cuts = max_edge_cuts(self)

        self.parts = collections.defaultdict(set)
        for node, part in self.assignment.items():
            self.parts[part].add(node)

    def _from_parent(self, parent, flips):
        self.parent = parent
        self.flips = flips

        self.assignment = {**parent.assignment, **flips}

        self.graph = parent.graph
        self.updaters = parent.updaters

        self.max_edge_cuts = parent.max_edge_cuts

        self._update_parts()

    def __repr__(self):
        number_of_parts = len(self)
        s = "s" if number_of_parts > 1 else ""
        return f"Partition of a graph into {str(number_of_parts)} part{s}"

    def __len__(self):
        return len(self.parts)

    def _update_parts(self):
        flows = flows_from_changes(self.parent.assignment, self.flips)

        # Parts must ontinue to be a defaultdict, so that new parts can appear.
        self.parts = collections.defaultdict(set, self.parent.parts)

        for part, flow in flows.items():
            self.parts[part] = (self.parent.parts[part] | flow['in']) - flow['out']

        # We do not want empty parts.
        self.parts = {part: nodes for part, nodes in self.parts.items() if len(nodes) > 0}

    def _update(self):
        self._cache = dict()

        for key in self.updaters:
            if key not in self._cache:
                self._cache[key] = self.updaters[key](self)

    def merge(self, flips):
        """
        :flips: dict assigning nodes of the graph to their new districts
        :returns: A new instance representing the partition obtained by performing the given flips
        on this partition.
        """

        return self.__class__(parent=self, flips=flips)

    def crosses_parts(self, edge):
        if type(edge) is not tuple:
            return self.assignment[edge[0]] != self.assignment[edge[1]]

    def initialize_statistic(self, field):
        """
        initialize_statistic computes the initial sum of the data column that
        we want to sum up for each district at each step.
        """
        statistic = collections.defaultdict(int)
        for node, part in self.assignment.items():
            vprop = self.graph.vertex_properties[field]
            statistic[part] += vprop[self.graph.vertex(node)]  # self.graph.vertex[node][field]
        return statistic

    def update_statistic(self, changes, old_statistic, field):
        """
        update_statistic returns the updated sum for the specificed statistic
        after changes are incorporated.
        """
        new_statistic = dict()
        for part, flow in flows_from_changes(self, changes).items():
            vprop = self.graph.vertex_properties[field]
            out_flow = sum(vprop[self.graph.vertex(node)] for node in flow['out'])
            in_flow = sum(vprop[self.graph.vertex(node)] for node in flow['in'])
            new_statistic[part] = old_statistic[part] - out_flow + in_flow
        return {**old_statistic, **new_statistic}

    def __getitem__(self, key):
        """Allows keying on a Partition instance.
        :key: Property to access.
        """
        if key not in self._cache:
            self._cache[key] = self.updaters[key](self)
        return self._cache[key]
