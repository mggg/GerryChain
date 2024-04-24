from functools import partial
from inspect import signature
import random

from gerrychain.partition import Partition
from ..tree import (
    epsilon_tree_bipartition,
    bipartition_tree,
    bipartition_tree_random,
    _bipartition_tree_random_all,
    uniform_spanning_tree,
    find_balanced_edge_cuts_memoization,
    ReselectException,
)
from typing import Callable, Optional, Dict, Union


class MetagraphError(Exception):
    """
    Raised when the partition we are trying to split is a low degree
    node in the metagraph.
    """

    pass


class ValueWarning(UserWarning):
    """
    Raised whe a particular value is technically valid, but may
    cause issues with the algorithm.
    """

    pass


def recom(
    partition: Partition,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    region_surcharge: Optional[Dict] = None,
    method: Callable = bipartition_tree,
) -> Partition:
    """
    ReCom (short for ReCombination) is a Markov Chain Monte Carlo (MCMC) algorithm
    used for redistricting. At each step of the algorithm, a pair of adjacent districts
    is selected at random and merged into a single district. The region is then split
    into two new districts by generating a spanning tree using the Kruskal/Karger
    algorithm and cutting an edge at random. The edge is checked to ensure that it
    separates the region into two new districts that are population balanced, and,
    if not, a new edge is selected at random and the process is repeated.

    Example usage:

    .. code-block:: python

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

    :param partition: The initial partition.
    :type partition: Partition
    :param pop_col: The name of the population column.
    :type pop_col: str
    :param pop_target: The target population for each district.
    :type pop_target: Union[int,float]
    :param epsilon: The epsilon value for population deviation as a percentage of the
        target population.
    :type epsilon: float
    :param node_repeats: The number of times to repeat the bipartitioning step. Default is 1.
    :type node_repeats: int, optional
    :param region_surcharge: The surcharge dictionary for the graph used for region-aware
        partitioning of the grid. Default is None.
    :type region_surcharge: Optional[Dict], optional
    :param method: The method used for bipartitioning the tree. Default is
        :func:`~gerrychain.tree.bipartition_tree`.
    :type method: Callable, optional

    :returns: The new partition resulting from the ReCom algorithm.
    :rtype: Partition
    """

    bad_district_pairs = set()
    n_parts = len(partition)
    tot_pairs = n_parts * (n_parts - 1) / 2  # n choose 2

    # Try to add the region aware in if the method accepts the surcharge dictionary
    if "region_surcharge" in signature(method).parameters:
        method = partial(method, region_surcharge=region_surcharge)

    while len(bad_district_pairs) < tot_pairs:
        try:
            while True:
                edge = random.choice(tuple(partition["cut_edges"]))
                # Need to sort the tuple so that the order is consistent
                # in the bad_district_pairs set
                parts_to_merge = [
                    partition.assignment.mapping[edge[0]],
                    partition.assignment.mapping[edge[1]],
                ]
                parts_to_merge.sort()

                if tuple(parts_to_merge) not in bad_district_pairs:
                    break

            subgraph = partition.graph.subgraph(
                partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
            )

            flips = epsilon_tree_bipartition(
                subgraph.graph,
                parts_to_merge,
                pop_col=pop_col,
                pop_target=pop_target,
                epsilon=epsilon,
                node_repeats=node_repeats,
                method=method,
            )
            break

        except Exception as e:
            if isinstance(e, ReselectException):
                bad_district_pairs.add(tuple(parts_to_merge))
                continue
            else:
                raise

    if len(bad_district_pairs) == tot_pairs:
        raise MetagraphError(
            f"Bipartitioning failed for all {tot_pairs} district pairs."
            f"Consider rerunning the chain with a different random seed."
        )

    return partition.flip(flips)


def reversible_recom(
    partition: Partition,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    balance_edge_fn: Callable = find_balanced_edge_cuts_memoization,
    M: int = 1,
    repeat_until_valid: bool = False,
    choice: Callable = random.choice,
) -> Partition:
    """
    Reversible ReCom algorithm for redistricting.

    This function performs the reversible ReCom algorithm, which is a Markov Chain Monte
    Carlo (MCMC) algorithm used for redistricting. For more information, see the paper
    "Spanning Tree Methods for Sampling Graph Partitions" by Cannon, et al. (2022) at
    https://arxiv.org/abs/2210.01401

    :param partition: The initial partition.
    :type partition: Partition
    :param pop_col: The name of the population column.
    :type pop_col: str
    :param pop_target: The target population for each district.
    :type pop_target: Union[int,float]
    :param epsilon: The epsilon value for population deviation as a percentage of the
        target population.
    :type epsilon: float
    :param balance_edge_fn: The balance edge function. Default is
        find_balanced_edge_cuts_memoization.
    :type balance_edge_fn: Callable, optional
    :param M: The maximum number of balance edges. Default is 1.
    :type M: int, optional
    :param repeat_until_valid: Flag indicating whether to repeat until a valid partition is
        found. Default is False.
    :type repeat_until_valid: bool, optional
    :param choice: The choice function for selecting a random element. Default is random.choice.
    :type choice: Callable, optional

    :returns: The new partition resulting from the reversible ReCom algorithm.
    :rtype: Partition
    """

    def dist_pair_edges(part, a, b):
        return set(
            e
            for e in part.graph.edges
            if (
                (
                    part.assignment.mapping[e[0]] == a
                    and part.assignment.mapping[e[1]] == b
                )
                or (
                    part.assignment.mapping[e[0]] == b
                    and part.assignment.mapping[e[1]] == a
                )
            )
        )

    def bounded_balance_edge_fn(*args, **kwargs):
        cuts = balance_edge_fn(*args, **kwargs)
        if len(cuts) > M:
            raise ReversibilityError(
                f"Found {len(cuts)} balance edges, " f"but the upper bound is {M}."
            )
        return cuts

    bipartition_tree_random_reversible = partial(
        _bipartition_tree_random_all,
        repeat_until_valid=repeat_until_valid,
        spanning_tree_fn=uniform_spanning_tree,
        balance_edge_fn=bounded_balance_edge_fn,
    )

    parts = sorted(list(partition.parts.keys()))
    dist_pairs = []
    for out_part in parts:
        for in_part in parts:
            dist_pairs.append((out_part, in_part))

    random_pair = random.choice(dist_pairs)
    pair_edges = dist_pair_edges(partition, *random_pair)
    if random_pair[0] == random_pair[1] or not pair_edges:
        return partition  # self-loop: no adjacency

    edge = random.choice(list(pair_edges))
    parts_to_merge = (
        partition.assignment.mapping[edge[0]],
        partition.assignment.mapping[edge[1]],
    )
    subgraph = partition.graph.subgraph(
        partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
    )

    all_cuts = bipartition_tree_random_reversible(
        subgraph, pop_col=pop_col, pop_target=pop_target, epsilon=epsilon
    )
    if not all_cuts:
        return partition  # self-loop: no balance edge

    nodes = choice(all_cuts).subset
    remaining_nodes = set(subgraph.nodes()) - set(nodes)
    flips = {
        **{node: parts_to_merge[0] for node in nodes},
        **{node: parts_to_merge[1] for node in remaining_nodes},
    }

    new_part = partition.flip(flips)
    seam_length = len(dist_pair_edges(new_part, *random_pair))

    prob = len(all_cuts) / (M * seam_length)
    if prob > 1:
        raise ReversibilityError(
            f"Found {len(all_cuts)} balance edges, but "
            f"the upper bound (with seam length 1) is {M}."
        )
    if random.random() < prob:
        return new_part

    return partition  # self-loop


class ReCom:
    """
    ReCom (short for ReCombination) is a class that represents a ReCom proposal
    for redistricting. It is used to create new partitions by recombining existing
    districts while maintaining population balance.

    """

    def __init__(
        self,
        pop_col: str,
        ideal_pop: Union[int, float],
        epsilon: float,
        method: Callable = bipartition_tree_random,
    ):
        """
        :param pop_col: The name of the column in the partition that contains the population data.
        :type pop_col: str
        :param ideal_pop: The ideal population for each district.
        :type ideal_pop: Union[int,float]
        :param epsilon: The epsilon value for population deviation as a percentage of the
            target population.
        :type epsilon: float
        :param method: The method used for bipartitioning the tree.
            Defaults to `bipartition_tree_random`.
        :type method: function, optional
        """
        self.pop_col = pop_col
        self.ideal_pop = ideal_pop
        self.epsilon = epsilon
        self.method = method

    def __call__(self, partition: Partition):
        return recom(
            partition, self.pop_col, self.ideal_pop, self.epsilon, method=self.method
        )


class ReversibilityError(Exception):
    """Raised when the cut edge upper bound is violated."""

    def __init__(self, msg):
        self.message = msg
