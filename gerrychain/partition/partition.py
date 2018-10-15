import collections

from gerrychain.graph import Graph
from gerrychain.updaters import (compute_edge_flows, cut_edges,
                                 flows_from_changes)


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
        :param graph: Underlying graph; a NetworkX object.
        :param assignment: Dictionary assigning nodes to districts. If None,
            initialized to assign all nodes to district 0.
        :param updaters: Dictionary of functions to track data about the partition.
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

        if isinstance(assignment, str):
            assignment = graph.assignment(assignment)
        elif not isinstance(assignment, dict):
            raise TypeError("Assignment must be a dict or a node attribute key")
        self.assignment = assignment

        if updaters is None:
            updaters = dict()
        self.updaters = self.default_updaters.copy()
        self.updaters.update(updaters)

        self.parent = None
        self.flips = None
        self.flows = None
        self.edge_flows = None

        self.parts = collections.defaultdict(set)
        for node, part in self.assignment.items():
            self.parts[part].add(node)

    def _from_parent(self, parent, flips):
        self.parent = parent
        self.flips = flips

        self.assignment = parent.assignment.copy()
        self.assignment.update(flips)

        self.graph = parent.graph
        self.parts = parent.parts
        self.updaters = parent.updaters

        self._update_flows()

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

    @classmethod
    def from_json_graph(cls, graph_path, assignment, updaters=None):
        """Creates a :class:`Partition` from a json file containing a
        serialized NetworkX `adjacency_data` object. Files of this
        kind for each state are available in the @gerrymandr/vtd-adjacency-graphs
        GitHub repository.

        :param graph_path: String filename for the json file
        :param assignment: String key for the node attribute giving a district
            assignment, or a dictionary mapping node IDs to district IDs.
        :param updaters: (optional) Dictionary of updater functions to
            attach to the partition, in addition to the default_updaters of `cls`.
        """
        graph = Graph.from_json(graph_path)
        return cls(graph, assignment, updaters)
