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


class Partition:
    """
    Partition represents a partition of the nodes of the graph. It will perform
    the first layer of computations at each step in the Markov chain - basic
    aggregations and calculations that we want to optimize.

    :graph: reference to the networkx graph
    :assignment: dictionary mapping nodes to their assigned parts of the partition
    """

    def __init__(self, graph, assignment):
        self.graph = graph
        self.assignment = assignment
        self.cut_edges = [edge for edge in self.graph.edges if self.crosses_parts(edge)]

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
        return Partition(self.graph, new_assignment)
