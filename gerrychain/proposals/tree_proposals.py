from ..random import random
from ..tree import recursive_tree_part, bipartition_tree, bipartition_tree_random


def recom(
    partition, pop_col, pop_target, epsilon, node_repeats=1, method=bipartition_tree
):
    """ReCom proposal.

    Description from MGGG's 2018 Virginia House of Delegates report:
    At each step, we (uniformly) randomly select a pair of adjacent districts and
    merge all of their blocks in to a single unit. Then, we generate a spanning tree
    for the blocks of the merged unit with the Kruskal/Karger algorithm. Finally,
    we cut an edge of the tree at random, checking that this separates the region
    into two new districts that are population balanced.

    Example usage::

        from functools import partial
        from gerrychain import MarkovChain
        from gerrychain.proposals import recom

        # ...define constraints, accept, partition, total_steps here...

        # Ideal population:
        pop_target = sum(partition["population"].values()) / len(partition)

        proposal = partial(
            recom, pop_col="POP10", pop_target=pop_target, epsilon=.05, node_repeats=10
        )

        chain = MarkovChain(proposal, constraints, accept, partition, total_steps)

    """
    edge = random.choice(tuple(partition["cut_edges"]))
    parts_to_merge = (partition.assignment[edge[0]], partition.assignment[edge[1]])

    subgraph = partition.graph.subgraph(
        partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
    )

    flips = recursive_tree_part(
        subgraph,
        parts_to_merge,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        method=method,
    )

    return partition.flip(flips)


class ReCom:
    def __init__(self, pop_col, ideal_pop, epsilon, method=bipartition_tree_random):
        self.pop_col = pop_col
        self.ideal_pop = ideal_pop
        self.epsilon = epsilon
        self.method = method

    def __call__(self, partition):
        return recom(
            partition, self.pop_col, self.ideal_pop, self.epsilon, method=self.method
        )
