from functools import partial
from inspect import signature
import random

from gerrychain.partition import Partition
from ..tree import (
    epsilon_tree_bipartition,
    bipartition_tree,
    bipartition_tree_random,
    bipartition_tree_random_with_num_cuts,
    uniform_spanning_tree,
    find_balanced_edge_cuts_memoization,
    ReselectException,
)
from typing import Callable, Optional, Dict, Union

# frm: only used in this file
class MetagraphError(Exception):
    """
    Raised when the partition we are trying to split is a low degree
    node in the metagraph.
    """

    pass


# frm: only used in this file
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
        print("bipartition_tree: updating restarts and attempts")
    :rtype: Partition
    """

    bad_district_pairs = set()
    n_parts = len(partition)
    tot_pairs = n_parts * (n_parts - 1) / 2  # n choose 2

    # frm: DBG: TODO: Remove this code
    # print(f"recom: all pairs of disctricts is: {tot_pairs}")
    # print(f"recom: method to do merge/split is: {method}")

    # Try to add the region aware in if the method accepts the surcharge dictionary
    if "region_surcharge" in signature(method).parameters:
        method = partial(method, region_surcharge=region_surcharge)
 
    while len(bad_district_pairs) < tot_pairs:
        # frm: In no particular order, try to merge and then split pairs of districts
        #       that have a cut_edge - meaning that they are adjacent, until you either
        #       find one that can be split, or you have tried all possible pairs
        #       of adjacent districts...
        try:
            # frm: TODO:  see if there is some way to avoid a while True loop...
            while True:
                edge = random.choice(tuple(partition["cut_edges"]))
                # Need to sort the tuple so that the order is consistent
                # in the bad_district_pairs set
                parts_to_merge = [
                    partition.assignment.mapping[edge[0]],
                    partition.assignment.mapping[edge[1]],
                ]
                parts_to_merge.sort()

                # frm: DBG: TODO: Remove this code
                # print(f"recom: districts to merge and split: {parts_to_merge}")
                # print(f"recom: first district nodes: {partition.parts[parts_to_merge[0]]}") 
                # print(f"recom: second district nodes: {partition.parts[parts_to_merge[1]]}") 

                if tuple(parts_to_merge) not in bad_district_pairs:
                    break

            # frm: Note that the vertical bar operator merges the two sets into one set.
            subgraph_nodes = partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]

            # print(f"recom: About to call epsilon_tree_bipartition()")
            flips = epsilon_tree_bipartition(
                partition.graph.subgraph(subgraph_nodes),
                parts_to_merge,
                pop_col=pop_col,
                pop_target=pop_target,
                epsilon=epsilon,
                node_repeats=node_repeats,
                method=method,
            )
            # print(f"recom: Finished calling epsilon_tree_bipartition()")
            # frm: DBG: TODO: Remove this code
            # print(f"recom: after epsilon_tree_bipartion: districts to merge and split: {parts_to_merge}")
            # print(f"recom: after epsilon_tree_bipartion: first district nodes: {partition.parts[parts_to_merge[0]]}") 
            # print(f"recom: after epsilon_tree_bipartion: second district nodes: {partition.parts[parts_to_merge[1]]}") 
            break

        except Exception as e:
            if isinstance(e, ReselectException):
                # frm: Add this pair to list of pairs that did not work...
                bad_district_pairs.add(tuple(parts_to_merge))
                continue
            else:
                raise

    if len(bad_district_pairs) == tot_pairs:
        raise MetagraphError(
            f"Bipartitioning failed for all {tot_pairs} district pairs."
            f"Consider rerunning the chain with a different random seed."
        )

    # print("recom: returning after successfully splitting two districts")
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
        frm: it returns a list of Cuts - a named tuple defined in tree.py
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
        # frm: Find all edges that cross from district a into district b
        return set(
            e
            # frm: TODO: edges vs. edge_ids:  edges are wanted here (tuples)
            # frm: Original Code:    for e in part.graph.edges
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

    """
    frm: Original Code:

    bipartition_tree_random_reversible = partial(
        _bipartition_tree_random_all,
        repeat_until_valid=repeat_until_valid,
        spanning_tree_fn=uniform_spanning_tree,
        balance_edge_fn=bounded_balance_edge_fn,
    )
    
    I deemed this code to be evil, if only because it used an internal tree.py routine
    _bipartition_tree_random_all().  This internal routine returns a set of Cut objects
    which otherwise never appear outside tree.py, so this just adds complexity.

    The only reason the original code used _bipartition_tree_random_all() instead of just
    using bipartition_tree_random() is that it needs to know how many possible new
    districts there are.  So, I created a new function in tree.py that does EXACTLY
    what bipartition_tree_random() does but which also returns the number of possible
    new districts.

    """
    bipartition_tree_random_reversible = partial(
        bipartition_tree_random_with_num_cuts,
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
    # Remember node_ids from which subgraph was created - we will need them below
    subgraph_nodes = partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]

    # frm: Note: This code has changed to make sure we don't access subgraph node_ids.
    #               The former code saved the subgraph and used its nodes to compute
    #               the remaining_nodes, but this doesn't work with RX, because the 
    #               node_ids for the subgraph are different from those in the parent graph.
    #               The solution is to just remember the parent node_ids that were used
    #               to create the subgraph, and to move the subgraph call in as an actual
    #               parameter, so that after the call there is no way to reference it.
    #
    #               Going forward, this should be a coding style - only invoke Graph.subgraph()
    #               as an actual parameter so that there is no way to inadvertently access
    #               the subgraph's node_ids afterwards.
    #
    num_possible_districts, nodes = bipartition_tree_random_reversible(
        partition.graph.subgraph(subgraph_nodes),
        pop_col=pop_col, pop_target=pop_target, epsilon=epsilon
    )
    if not nodes:
        return partition  # self-loop: no balance edge

    remaining_nodes = subgraph_nodes - set(nodes)
    # frm: Notes to Self:  the ** operator below merges the two dicts into a single dict.
    flips = {
        **{node: parts_to_merge[0] for node in nodes},
        **{node: parts_to_merge[1] for node in remaining_nodes},
    }

    new_part = partition.flip(flips)
    seam_length = len(dist_pair_edges(new_part, *random_pair))

    prob = num_possible_districts / (M * seam_length)
    if prob > 1:
        raise ReversibilityError(
            f"Found {len(all_cuts)} balance edges, but "
            f"the upper bound (with seam length 1) is {M}."
        )
    if random.random() < prob:
        return new_part

    return partition  # self-loop


# frm ???:  I do not think that ReCom() is ever called.  Note that it 
#           only defines a constructor and a __call__() which would allow
#           you to call the recom() function by creating a ReCom object and then 
#           "calling" that object - why not just call the recom function?
#
#           ...confused...
#
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
