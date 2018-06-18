import random


def propose_random_flip(partition):
    """Proposes a random boundary flip from the partition.

    :partition: The current partition to propose a flip from.
    :return: a dictionary of with the flipped node mapped to its new assignment
    """
    # TODO fix empty array issue
    # also note only flipping 1 edge for testing purposes!!
    edge = partition.graph.edge(partition.graph.vertex(0), partition.graph.vertex(8))
    index = random.choice((0, 1))

    if index == 1:
        flipped_node, other_node = edge.source(), edge.target()
    else:
        flipped_node, other_node = edge.target(), edge.source()
    flip = dict([(flipped_node, partition.assignment[other_node])])

    return flip


class Partition:
    """Partition represents a partition of the nodes of the graph. It will perform
    the first layer of computations at each step in the Markov chain - basic
    aggregations and calculations that we want to optimize.

    :graph: reference to the networkx graph
    :assignment: dictionary mapping nodes to their assigned parts of the partition
    """

    def __init__(self, graph, assignment, updaters=None, fields=None):
        self.graph = graph
        self.assignment = assignment

        if not updaters:
            updaters = dict()
        self.updaters = updaters

        if not fields:
            fields = {key: updater(self) for key, updater in self.updaters.items()}
        self.fields = fields

        self.cut_edges = [edge for edge in self.graph.edges if self.crosses_parts(edge)]

    def crosses_parts(self, edge):
        return self.assignment[edge.source()] != self.assignment[edge.target()]

    def merge(self, flips):
        """Takes a dictionary of new assignments and returns the Partition
        obtained by applying these new assignments to this instance (self)
        of Partition.

        :flips: a dictionary of nodes mapped to their new assignments
        :return: a new Partition instance
        """
        new_assignment = {**self.assignment, **flips}

        new_fields = {key: updater(self, flips) for key, updater in self.updaters.items()}

        return Partition(self.graph, assignment=new_assignment,
                         updaters=self.updaters, fields=new_fields)

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
        return self.fields[key]