import collections
import random

Flip = collections.namedtuple('Flip', ['node', 'assign_to'])


class Partition:
    def __init__(self, graph, assignment, cut_edges=None):
        self.graph = graph
        self.assignment = assignment
        self.cut_edges = set(edge for edge in self.graph.edges if self.crosses_parts(edge))

    def crosses_parts(self, edge):
        return self.assignment(edge[0]) == self.assignment(edge[1])

    def apply_flip(self, flip):
        new_assignment = collections.ChainMap(self.assignment, dict([flip.node, flip.assign_to]))
        return Partition(self.graph, new_assignment)

    def possible_flips(self):
        for edge in self.cut_edges:
            index = random.choice([0, 1])
            flipped_node, other_node = edge[index], edge[1 - index]
            yield Flip(node=flipped_node, assign_to=self.assignment[other_node])


class MarkovChain:
    def __init__(self, proposal, is_valid, accept, initial_state, total_steps=1000):
        self.proposal = proposal
        self.is_valid = is_valid
        self.accept = accept
        self.total_steps = total_steps
        self.state = initial_state

    def __iter__(self):
        self.counter = 0
        return self

    def __next__(self):
        while self.counter < self.total_steps:
            proposal = self.proposal(self.state)
            if self.is_valid(proposal):
                if self.accept(proposal):
                    self.state = proposal
                yield proposal
        raise StopIteration


# class PartitionsMetaGraph:
#     def __init__(self, graph, criteria):
#         self.graph = graph
#         self.criteria = criteria

#     def check_criteria(self, partition, step):
#         uncut_edges = set(self.graph.edges) - partition.cut_edges
#         # Is this what we want to pass to the functions?
#         # We should ask other teams what makes the most sense for them.
#         #
#         # I think we might want to just give the graph with subsets of nodes
#         # for the different components
#         hypothetical_graph = self.graph.edge_subgraph(uncut_edges)
#         return all(criterion(hypothetical_graph) for criterion in self.criteria)
