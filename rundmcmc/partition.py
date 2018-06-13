import collections
import random


def propose_random_flip(partition):
    """
    Proposes a random boundary flip from the partition.

    :partition: The current partition to propose a flip from.
    :return: a dictionary of with the flipped node mapped to its new assignment
    """
    edge = random.choice(partition.cut_edges)
    index = random.choice((0, 1))

    flipped_node, other_node = edge[index], edge[1 - index]
    flip = dict([(flipped_node, partition.assignment[other_node])])

    return flip


def create_flow():
    return {'in': set(), 'out': set()}


def flows_from_changes(partition, changes):
    flows = collections.defaultdict(create_flow)
    for node, target in changes.items():
        source = partition.assignment[node]
        if source != target:
            flows[target]['in'].add(node)
            flows[source]['out'].add(node)
    return flows


class Partition:
    """
    Partition represents a partition of the nodes of the graph. It will perform
    the first layer of computations at each step in the Markov chain - basic
    aggregations and calculations that we want to optimize.

    :graph: reference to the networkx graph
    :assignment: dictionary mapping nodes to their assigned parts of the partition
    """

    def __init__(self, graph, assignment, aggregate_fields=None, overwrite_stats=None):
        self.graph = graph
        self.assignment = assignment
        self.cut_edges = [edge for edge in self.graph.edges if self.crosses_parts(edge)]

        if aggregate_fields:
            self.statistics = {field: dict() for field in aggregate_fields}
        else:
            self.statistics = dict()

        if not overwrite_stats:
            if aggregate_fields:
                self.statistics = {field: self.initialize_statistic(
                    field) for field in aggregate_fields}
        else:
            self.statistics = overwrite_stats

    def crosses_parts(self, edge):
        return self.assignment[edge[0]] != self.assignment[edge[1]]

    def merge(self, flips):
        """
        Takes a dictionary of new assignments and returns the Partition obtained
        by applying these new assignments to this instance (self) of Partition.

        :flips: a dictionary of nodes mapped to their new assignments
        :return: a new Partition instance
        """
        new_assignment = {**self.assignment, **flips}

        new_stats = {field: self.update_statistic(
            flips, statistic, field) for field, statistic in self.statistics.items()}

        return Partition(self.graph, new_assignment, overwrite_stats=new_stats)

    def initialize_statistic(self, field):
        """
        initialize_statistic computes the initial sum of the data column that
        we want to sum up for each district at each step.
        """
        statistic = collections.defaultdict(int)
        for node, part in self.assignment.items():
            statistic[part] += self.graph.nodes[node][field]
        return statistic

    def update_statistic(self, changes, old_statistic, field):
        """
        update_statistic returns the updated sum for the specificed statistic
        after changes are incorporated.
        """
        new_statistic = dict()
        for part, flow in flows_from_changes(self, changes).items():
            out_flow = sum(self.graph.nodes[node][field] for node in flow['out'])
            in_flow = sum(self.graph.nodes[node][field] for node in flow['in'])
            new_statistic[part] = old_statistic[part] - out_flow + in_flow
        return {**old_statistic, **new_statistic}
