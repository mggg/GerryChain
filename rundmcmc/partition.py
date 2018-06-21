import random


def propose_random_flip(partition):
    """Proposes a random boundary flip from the partition.

    :partition: The current partition to propose a flip from.
    :returns: a dictionary of with the flipped node mapped to its new assignment

    """
    edge = random.choice(tuple(partition['cut_edges']))
    index = random.choice((0, 1))

    flipped_node, other_node = edge[index], edge[1 - index]
    flip = {flipped_node: partition.assignment[other_node]}

    return flip


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

    def _from_parent(self, parent, flips):
        self.parent = parent
        self.flips = flips

        self.graph = parent.graph
        self.updaters = parent.updaters

        self.assignment = {**parent.assignment, **self.flips}

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
            self._cache[key] = self.updaters[key](self, self.parent, self.flips)
        return self._cache[key]
