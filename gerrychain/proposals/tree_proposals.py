import random
from functools import partial
from inspect import signature
from typing import Callable, Dict, Optional, Sequence, Union

from gerrychain.partition import Partition

from ..graph import Graph
from ..tree import (  # epsilon_tree_bipartition,
    BalanceError,
    PopulationBalanceError,
    ReselectException,
    bipartition_tree,
    bipartition_tree_random_with_num_cuts,
    find_balanced_edge_cuts_memoization,
    uniform_spanning_tree,
)


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


def epsilon_tree_bipartition(
    subgraph_to_split: Graph,
    parts: Sequence,
    pop_target: Union[float, int],
    pop_col: str,
    epsilon: float,
    node_repeats: int = 1,
    bipartition_tree_fn: Callable = partial(bipartition_tree, max_attempts=10000),
) -> Dict:
    """
    Uses :func:`~gerrychain.tree.bipartition_tree` to partition a tree into
    two parts of population ``pop_target`` (within ``epsilon``).

    Args:
        graph (Graph): The graph to partition into two :math:`\varepsilon`-balanced parts.
        parts (Sequence): Iterable of part (district) labels (like ``[0,1,2]`` or ``range(4)``).
        pop_target (Union[float, int]): Target population for each part of the partition.
        pop_col (str): Node attribute key holding population data.
        epsilon (float): How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
            of the partition can be.
        node_repeats (int, optional): Parameter for :func:`~gerrychain.tree.bipartition_tree` to
            use. Defaults to 1.
        bipartition_tree_fn (Callable, optional): The partition method to use. Defaults to
            `partial(bipartition_tree, max_attempts=10000)`.

    Returns:
        dict: New assignments for the nodes of ``graph``.
    """
    if len(parts) != 2:
        raise ValueError(
            "This function only supports bipartitioning. Please ensure that there"
            + " are exactly 2 parts in the parts list."
        )

    flips = {}
    remaining_nodes = subgraph_to_split.node_indices

    lb_pop = pop_target * (1 - epsilon)
    ub_pop = pop_target * (1 + epsilon)
    check_pop = lambda x: lb_pop <= x <= ub_pop

    nodes = bipartition_tree_fn(
        subgraph_to_split.subgraph(remaining_nodes),
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        one_sided_cut=False,
    )

    if nodes is None:
        raise BalanceError()

    # Calculate the total population for the two districts based on the
    # results of the "bipartition_tree_fn()" partitioning.
    part_pop = 0
    for node in nodes:
        # frm: ???:  The code above has already confirmed that len(parts) is 2
        #               so why use negative index values - why not just use
        #               parts[0] and parts[1]?
        flips[node] = parts[-2]
        part_pop += subgraph_to_split.node_data(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    remaining_nodes -= nodes

    # All of the remaining nodes go in the last part
    part_pop = 0
    for node in remaining_nodes:
        flips[node] = parts[-1]
        part_pop += subgraph_to_split.node_data(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    # translate subgraph node_ids back into node_ids in parent graph
    translated_flips = subgraph_to_split.translate_subgraph_node_ids_for_flips(flips)

    return translated_flips


def recom(
    partition: Partition,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    region_surcharge: Optional[Dict] = None,
    bipartition_tree_fn: Callable = bipartition_tree,
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

    Args:
        partition (Partition): The initial partition.
        pop_col (str): The name of the population column.
        pop_target (Union[int,float]): The target population for each district.
        epsilon (float): The epsilon value for population deviation as a percentage of the target
            population.
        node_repeats (int, optional): The number of times to repeat the bipartitioning step. Default
            is 1.
        region_surcharge (Optional[Dict], optional): The surcharge dictionary for the graph used for
            region-aware partitioning of the grid. Default is None.
        bipartition_tree_fn (Callable, optional): The method used for bipartitioning the tree.
            Default is :func:`~gerrychain.tree.bipartition_tree`.

    Returns:
        Partition: The new partition resulting from the ReCom algorithm.
    """

    bad_district_pairs = set()
    n_parts = len(partition)
    tot_pairs = n_parts * (n_parts - 1) / 2  # n choose 2

    # Try to add the region aware in if the bipartition_tree_fn accepts the surcharge dictionary
    if "region_surcharge" in signature(bipartition_tree_fn).parameters:
        bipartition_tree_fn = partial(bipartition_tree_fn, region_surcharge=region_surcharge)

    # frm: TODO: Refactoring:  Should we sanity check region_surcharge usage?
    #
    # If the caller passed in a non-None value for region_surcharge, then presumably
    # he/she should have also passed in a function for the "bipartition_tree_fn" parameter that
    # accepts a region_surcharge parameter.
    #
    # Peter said (January 2026): A lot of our users are not coders, so they
    # do silly things. I'm open to changing this to have it just fail if the
    # bipartition_tree_fn does not have the corresponding parameter, but we should have
    # a defensive pattern here.
    #

    while len(bad_district_pairs) < tot_pairs:
        # frm: TODO: Documentation: Confirm that this comment is accurate:
        #
        #  In no particular order, try to merge and then split pairs of districts
        #  that have a cut_edge - meaning that they are adjacent, until you either
        #  find one that can be split, or you have tried all possible pairs
        #  of adjacent districts...
        #
        try:
            # frm: TODO: Refactoring:  see if there is some way to avoid a while True loop...
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

            # frm: Note that the vertical bar operator merges the two sets into one set.
            subgraph_nodes = partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]

            flips = epsilon_tree_bipartition(
                partition.graph.subgraph(subgraph_nodes),
                parts_to_merge,
                pop_col=pop_col,
                pop_target=pop_target,
                epsilon=epsilon,
                node_repeats=node_repeats,
                bipartition_tree_fn=bipartition_tree_fn,
            )
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

    return partition.flip(flips)


# frm: TODO: Refactoring: Change name and default value of M below.
#
# Peter said (January 2026):
#
# This comes from the paper in section 3.2:
#
# https://mggg.org/rrc
#
# But M is a terrible name for a parameter, and we should force the user to
# provide this. 1 is actually the worst value that this could be since
# this should be a global upper bound..


def reversible_recom(
    partition: Partition,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    find_balanced_edge_cuts_fn: Callable = find_balanced_edge_cuts_memoization,
    M: int = 1,  # frm: TODO: Documentation: WTF does 'M' stand for?
    repeat_until_valid: bool = False,
    choice: Callable = random.choice,
) -> Partition:
    """
    Reversible ReCom algorithm for redistricting.

    This function performs the reversible ReCom algorithm, which is a Markov Chain Monte
    Carlo (MCMC) algorithm used for redistricting. For more information, see the paper
    "Spanning Tree Methods for Sampling Graph Partitions" by Cannon, et al. (2022) at
    https://arxiv.org/abs/2210.01401

    Args:
        partition (Partition): The initial partition.
        pop_col (str): The name of the population column.
        pop_target (Union[int,float]): The target population for each district.
        epsilon (float): The epsilon value for population deviation as a percentage of the target
            population.
        find_balanced_edge_cuts_fn (Callable, optional): The balance edge function. Default is
            find_balanced_edge_cuts_memoization.
        M (int, optional): The maximum number of balance edges. Default is 1.
        repeat_until_valid (bool, optional): Flag indicating whether to repeat until a valid
            partition is found. Default is False.
        choice (Callable, optional): The choice function for selecting a random element. Default is
            random.choice.

    Returns:
        Partition: The new partition resulting from the reversible ReCom algorithm.
    """

    def dist_pair_edges(part, a, b):
        # frm: Find all edges that cross from district a into district b
        return set(
            e
            for e in part.graph.edges
            if (
                (part.assignment.mapping[e[0]] == a and part.assignment.mapping[e[1]] == b)
                or (part.assignment.mapping[e[0]] == b and part.assignment.mapping[e[1]] == a)
            )
        )

    # frm: TODO: Refactoring: Get rid of *args and **kwargs below.
    #
    # The reason for this hack is that the signatures for the different find_balanced_edge_cuts_fn's
    # are different, so the "bounded_find_balanced_edge_cuts_fn" cannot know exactly what params
    # make sense.  The *args, and **kwargs just allow it to ignorantly pass through whatever
    # it gets, hoping that they make sense for the balance_edge_fun cal.
    #
    # The way out of this is to normalize the signatures for all balanced edge functions so
    # that we know what the parameters are in all cases.  Then we can just use those
    # canonical parameters below.

    def bounded_find_balanced_edge_cuts_fn(*args, **kwargs):
        cuts = find_balanced_edge_cuts_fn(*args, **kwargs)
        if len(cuts) > M:
            raise ReversibilityError(
                f"Found {len(cuts)} balance edges, " f"but the upper bound is {M}."
            )
        return cuts

    parts = sorted(list(partition.parts.keys()))
    dist_pairs = []
    for out_part in parts:
        for in_part in parts:
            dist_pairs.append((out_part, in_part))
            # frm: TODO: Code: ???:   Grok why this code considers pairs that are the same part...
            #
            # For instance, if there are only two parts (districts), then this code will
            # produce four pairs: (0,0), (0,1), (1,0), (1,1).  The code below tests
            # to see if there is any adjacency, but there will never be adjacency between
            # the same part (district).  Why not just prune out all pairs that have the
            # same two values and save an interation of the entire chain?
            #
            # Stated differently, is there any value in doing an entire chain iteration
            # when we randomly select the same part (district) to merge with itself???
            #
            # A similar issue comes up if there are no pair_edges (below).  We waste
            # an entire iteration in that case too - which seems kind of dumb...
            #

    random_pair = random.choice(dist_pairs)
    pair_edges = dist_pair_edges(partition, *random_pair)
    if random_pair[0] == random_pair[1] or not pair_edges:
        return partition  # self-loop: no adjacency

    # frm: TODO: Code: ???:  Grok why it is OK to return the partition unchanged as the next step.
    #
    # This runs the risk of running an entire chain without ever changing the partition.
    # I assume that the logic is that there is deliberate randomness introduced each time,
    # so eventually, if it is possible, the chain will get started, but it seems like there
    # should be some kind of check to see if it doesn't ever get started, so that the
    # user can have a clue about what is going on...
    #
    # Peter said (in December 2025): The long and the short of why we have all of
    # these weird conditions here is because Reversible ReCom targets the spanning
    # tree distribution. By modifying how the acceptance of partituclar partitioning
    # schemes is handled, we are able to sample exactly from that distribution
    # rather than an approximation of it like we do in regular ReCom.
    #
    # So maybe this is really just a documentation issue now...

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

    result = bipartition_tree_random_with_num_cuts(
        partition.graph.subgraph(subgraph_nodes),
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        repeat_until_valid=repeat_until_valid,
        spanning_tree_fn=uniform_spanning_tree,
        find_balanced_edge_cuts_fn=bounded_find_balanced_edge_cuts_fn,
    )
    num_possible_districts, nodes = result
    if num_possible_districts == 0:
        return partition  # self-loop: no balance edge

    remaining_nodes = subgraph_nodes - set(nodes)
    # Note:  Clever way to create a single dictionary from
    # two dictionaries - the ** operator unpacks each dictionary
    # and then they get merged into a new dictionary.
    flips = {
        **{node: parts_to_merge[0] for node in nodes},
        **{node: parts_to_merge[1] for node in remaining_nodes},
    }

    new_part = partition.flip(flips)
    seam_length = len(dist_pair_edges(new_part, *random_pair))

    prob = num_possible_districts / (M * seam_length)
    if prob > 1:
        raise ReversibilityError(
            f"Found {len(result) if result is not None else 0} balance edges, but "
            f"the upper bound (with seam length 1) is {M}."
        )
    if random.random() < prob:
        return new_part

    return partition  # self-loop


# frm TODO: Refactoring:  Finish making class ReCom useful...
#
# Peter responded in a January 2026 code review that he thinks the purpose
# of the ReCom class is to make it easier for folks who find partial functions
# odd/confusing.  The idea is that this class can be used instead of creating
# a partial function.
#
# I have to admit that I personally find using a class instead of a
# partial function MORE confusing, but whatever.
#
# Here is what Peter said in the PR (with some comments by me afterwards):
#
# I am not so sure that we want to get rid of this. I think that this was
# built by someone trying to solve the problem where, when a user wants
# to run a chain with ReCom, they have to do the following bit of
# syntax twister:
#
#     from functools import partial
#
#     proposal = partial(
#         recom,
#         pop_col="TOTPOP",
#         pop_target=ideal_population,
#         epsilon=0.01,
#         node_repeats=2
#     )
#
# This partial application is familiar to anyone that does
# functional programming, and is effectively just
#
#     def proposal(state: Partition) -> Partition:
#         return recom(
#             state,
#             pop_col="TOTPOP",
#             pop_target=ideal_population,
#             epsilon=0.01,
#             node_repeats=2,
#         )
#
# in disguise. But our users are not programmers, and I get a
# lot of questions about the "partial" function that appears
# in the documentation. The ReCom class does this partial application
# under the hood using its __call__ attribute, and eliminates the need
# for the import of partial from functools, so the user only has to do
#
#     Recom(
#         pop_col="TOTPOP",
#         ideal_pop=ideal_population,
#         epsilon=0.01,
#     )
#
# rather than the partial rigmarole.
#
# I discovered this class existed in the codebase after doing a big
# refresh on the main documentation a while ago. I have been waiting
# to update things until a major release because the values that need
# to be passed to the __init__ of Recom depend on the underlying
# bipartition function, and the class would probably be better
# transformed into something closer to a "namespace" to improve
# discoverability
#
# class ReCom:
#     def __init__(self, *args, **kwargs):
#         raise TypeError("ReCom is not instantiable; use ReCom.mst(...), etc.")
#
#     @classmethod
#     def mst(...):
#         # minimum spanning tree version
#
#     @classmethod
#     def B(...):
#         # This is the "district pairs minimum spanning tree".  An absolutely terrible name
#         # for a function, to be sure, but it will make replication of what is in the
#         # Reversible ReCom paper (https://data-democracy.org/rrc) we published a while
#         # back easier for other people. This function would just be a wrapper around mst
#         # defined above.
#
# and so on. I am happy to put all of this functionality in later if you don't
# want to mess with it..
#
# ===========================================
# Fred's comments to Peter's remarks above:
#
# Firstly a nit: Peter should have said ReCom(...) instead of Recom()...
#
# As Peter points out, there is the issue of passing the proper set of parameters
# to the ReCom __init__() function.  Given the recent update to tree.py - creating
# a new module bipartition_tree.py with a unified bipartition_tree approach
# using _internal_bipartition_tree(), the set of parameters for the ReCom
# constructor would just be the set of parameters to _internal_bipartition_tree(),
# which unfortunately is a long list.
#
# Peter's other approach, to create a bunch of specific routines (via a namespace
# approach) would allow the user to deal with fewer parameters - only providing
# the ones needed).  I presume that the implementation for each of these
# class methods would just be a partial function.
#
# So this is kind of just syntactic sugar, but hey sugar tastes good!
#
# One nice thing about this approach is that it is a way to make it obvious
# to people what the standard ways of doing things are, and it provides
# the opportunity to introduce a user to partial functions, by adding
# comments in the ReCom class that tell the user that he/she can create
# his/her own ReCom function by just creating their own partial function.
# Stated differently, this provides a very nice, logical, discoverable
# place in the codebase for a user to grok how the recom approach works
# and how to extend it if he/she would like to.
#
# My only question to Peter is how this namespace should look.  I think
# the following is what would be the first step, and then Peter could
# add more later:
#
#     from functools import partial
#
#     class ReCom:
#
#         def __init__(self, *args, **kwargs):
#             raise TypeError("ReCom is not instantiable; use ReCom.mst(...), etc.")
#
#         @classmethod
#         def std_recom_proposal(
#             partition: Partition,
#             pop_col: str,
#             pop_target: Union[int, float],
#             epsilon: float,
#             node_repeats: int = 1,
#             region_surcharge: Optional[Dict] = None,
#             bipartition_tree_fn: Callable = bipartition_tree,
#         ) -> Partition:
#             new_proposal = partial(
#                 recom,
#                 pop_col = pop_col,
#                 pop_target = pop_target,
#                 epsilon = epsilon,
#                 node_repeats = node_repeats,
#                 region_surcharge =  region_surcharge,
#                 bipartition_tree_fn = bipartition_tree_fn,
#             )
#             return new_proposal
#
#         @classmethod
#         def mst(...):
#             # minimum spanning tree version


#         @classmethod
#         def B(...):
#             # This is the "district pairs minimum spanning tree".  An absolutely terrible name
#             # for a function, to be sure, but it will make replication of what is in the
#             # Reversible ReCom paper (https://data-democracy.org/rrc) we published a while
#             # back easier for other people. This function would just be a wrapper around mst
#             # defined above..
#
# and then a user could just do:
#
#     my_proposal = ReCom.std_recom_proposal(
#         pop_col="TOTPOP",
#         pop_target=ideal_population,
#         epsilon=0.01,
#         node_repeats=2
#     )
#
# Peter: Is this what you had in mind?
#
# ===========================================
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
        bipartition_tree_fn: Callable = bipartition_tree,
    ):
        """
        Args:
            pop_col (str): The name of the column in the partition that contains the population
                data.
            ideal_pop (Union[int,float]): The ideal population for each district.
            epsilon (float): The epsilon value for population deviation as a percentage of the
                target population.
            bipartition_tree_fn (function, optional): The method used for bipartitioning the tree.
                Defaults to `bipartition_tree`.
        """
        self.pop_col = pop_col
        self.ideal_pop = ideal_pop
        self.epsilon = epsilon
        self.bipartition_tree_fn = bipartition_tree_fn

    def __call__(self, partition: Partition):
        return recom(
            partition,
            self.pop_col,
            self.ideal_pop,
            self.epsilon,
            bipartition_tree_fn=self.bipartition_tree_fn,
        )


class ReversibilityError(Exception):
    """Raised when the cut edge upper bound is violated."""

    def __init__(self, msg):
        self.message = msg
