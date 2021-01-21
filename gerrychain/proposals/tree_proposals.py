from functools import partial
from ..random import random

from ..tree import (
    recursive_tree_part, bipartition_tree, bipartition_tree_random,
    uniform_spanning_tree, find_balanced_edge_cuts_memoization,
    BalanceError
)


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


def reversible_recom(partition, pop_col, pop_target, epsilon,
                     balance_edge_fn=find_balanced_edge_cuts_memoization, M=1,
                     repeat_until_valid=False):
    def dist_pair_edges(part, a, b):
        return set(
            e for e in part.graph.edges
            if ((part.assignment[e[0]] == a and part.assignment[e[1]] == b) or
                (part.assignment[e[0]] == b and part.assignment[e[1]] == a))
        )

    def bounded_balance_edge_fn(*args, **kwargs):
        cuts = balance_edge_fn(*args, **kwargs)
        if len(cuts) > M:
            raise ReversibilityError(f'Found {len(cuts)} balance edges, '
                                     f'but the upper bound is {M}.')
        return cuts

    bipartition_tree_random_reversible = partial(
        bipartition_tree_random,
        repeat_until_valid=repeat_until_valid,
        spanning_tree_fn=uniform_spanning_tree,
        balance_edge_fn=bounded_balance_edge_fn
    )

    parts = sorted(list(partition.parts.keys()))
    dist_pairs = []
    for out_part in parts:
        for in_part in parts:
            dist_pairs.append((out_part, in_part))

    random_pair = random.choice(dist_pairs)
    pair_edges = dist_pair_edges(partition, *random_pair)
    if random_pair[0] == random_pair[1] or not pair_edges:
        return partition    # self-loop: no adjacency

    edge = random.choice(list(pair_edges))
    parts_to_merge = (partition.assignment[edge[0]], partition.assignment[edge[1]])
    subgraph = partition.graph.subgraph(
        partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
    )

    try:
        flips = recursive_tree_part(
            subgraph,
            parts_to_merge,
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            method=bipartition_tree_random_reversible
        )
    except BalanceError:
        return partition    # self-loop: no balance edge

    new_part = partition.flip(flips)
    seam_length = len(dist_pair_edges(new_part, *random_pair))

    if random.random() < 1 / (M * seam_length):
        return new_part

    return partition     # self-loop


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


class ReversibilityError(Exception):
    """Raised when the cut edge upper bound is violated."""
    def __init__(self, msg):
        self.message = msg
