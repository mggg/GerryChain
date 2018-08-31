import collections

from rundmcmc.proposals import max_edge_cuts
from rundmcmc.updaters import flows_from_changes, compute_edge_flows, cut_edges


class Partition:
    """
    Partition represents a partition of the nodes of the graph. It will perform
    the first layer of computations at each step in the Markov chain - basic
    aggregations and calculations that we want to optimize.

    """
    default_updaters = {'cut_edges': cut_edges}

    def __init__(self, graph=None, assignment=None, updaters=None,
                 parent=None, flips=None):
        """
        :graph: Underlying graph; a NetworkX object.
        :assignment: Dictionary assigning nodes to districts. If None,
                     initialized to assign all nodes to district 0.
        :updaters: Dictionary of functions to track data about the partition.
                   The keys are stored as attributes on the partition class,
                   which the functions compute.

        """
        if parent:
            self._from_parent(parent, flips)
            self._update()
        else:
            self._first_time(graph, assignment, updaters)
            self._update()
            self.parts = tuple(self.parts.keys())

    def _first_time(self, graph, assignment, updaters):
        self.graph = graph
        self.assignment = assignment

        if not updaters:
            updaters = dict()

        self.updaters = {**self.default_updaters, **updaters}

        self.parent = None
        self.flips = None
        self.flows = None
        self.edge_flows = None

        self.parts = collections.defaultdict(set)
        for node, part in self.assignment.items():
            self.parts[part].add(node)

        self.max_edge_cuts = max_edge_cuts(self)

    def _from_parent(self, parent, flips):
        self.parent = parent
        self.flips = flips

        self.assignment = {**parent.assignment, **flips}

        self.graph = parent.graph
        self.parts = parent.parts
        self.updaters = parent.updaters

        self._update_flows()

        self.max_edge_cuts = parent.max_edge_cuts

    def __repr__(self):
        number_of_parts = len(self)
        s = "s" if number_of_parts > 1 else ""
        return "Partition of a graph into {} part{}".format(number_of_parts, s)

    def __len__(self):
        return len(self.parts)

    def _update_flows(self):
        self.flows = flows_from_changes(self.parent.assignment, self.flips)
        self.edge_flows = compute_edge_flows(self)

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
        return self.assignment[edge[0]] != self.assignment[edge[1]]

    def __getitem__(self, key):
        """Allows keying on a Partition instance.

        :key: Property to access.

        """
        if key not in self._cache:
            self._cache[key] = self.updaters[key](self)
        return self._cache[key]
