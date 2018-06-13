import collections
import random

Flip = collections.namedtuple('Flip', ['node', 'assign_to'])


def propose_random_flip(partition):
    edge = random.choice(partition.cut_edges)
    index = random.choice((0, 1))

    flipped_node, other_node = edge[index], edge[1 - index]
    flip = dict([(flipped_node, partition.assignment[other_node])])

    return flip


class Partition:
    def __init__(self, graph, assignment):
        self.graph = graph
        self.assignment = assignment
        self.cut_edges = [edge for edge in self.graph.edges if self.crosses_parts(edge)]

    def crosses_parts(self, edge):
        return self.assignment[edge[0]] != self.assignment[edge[1]]

    def merge(self, flips):
        new_assignment = {**self.assignment, **flips}
        return Partition(self.graph, new_assignment)


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
            proposed_next_state = self.state.merge(proposal)
            if self.is_valid(proposed_next_state):
                if self.accept(proposed_next_state):
                    self.state = proposed_next_state
                yield proposed_next_state
        raise StopIteration
