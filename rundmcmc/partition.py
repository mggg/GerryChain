import collections

from rundmcmc.updaters import flows_from_changes


class Partition:
    """
    Partition represents a partition of the nodes of the graph. It will perform
    the first layer of computations at each step in the Markov chain - basic
    aggregations and calculations that we want to optimize.

    """

    def __init__(self, graph=None, assignment=None, updaters=None,
                 parent=None, flips=None):
        if parent:
            self._from_parent(parent, flips)
        else:
            self._first_time(graph, assignment, updaters)

        self._update()

    def _first_time(self, graph, assignment, updaters):
        self.graph = graph
        self.assignment = assignment
        self.updaters = updaters

        self.parent = None
        self.flips = None

        self.parts = collections.defaultdict(set)
        for node, part in self.assignment.items():
            self.parts[part].add(node)

    def _from_parent(self, parent, flips):
        self.parent = parent
        self.flips = flips

        self.assignment = {**parent.assignment, **flips}

        self.graph = parent.graph
        self.updaters = parent.updaters

        self._update_parts()

    def _update_parts(self):
        flows = flows_from_changes(self.parent.assignment, self.flips)
        self.parts = {part: self.parent.parts[part] for part in self.parent.parts}
        for part, flow in flows.items():
            self.parts[part] = (self.parent.parts[part] | flow['in']) - flow['out']

    def _update(self):
        self._cache = dict()

        for key in self.updaters:
            if key not in self._cache:
                self._cache[key] = self.updaters[key](self)

    def merge(self, flips):
        return Partition(parent=self, flips=flips)

    def crosses_parts(self, edge):
        return self.assignment[edge[0]] != self.assignment[edge[1]]

    def __getitem__(self, key):
        """Allows keying on a Partition instance.
        :key: Property to access.
        """
        if key not in self._cache:
            self._cache[key] = self.updaters[key](self)
        return self._cache[key]
