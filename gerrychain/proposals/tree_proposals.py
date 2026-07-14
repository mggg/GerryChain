import random
from collections.abc import Callable, Hashable, Iterable, Iterator, Sequence, Set as AbstractSet
from functools import partial
from typing import Literal, cast

from gerrychain._rng import make_rng
from gerrychain.partition import Partition

from ..graph import FrozenGraph, Graph
from ..tree import (  # epsilon_tree_bipartition,
    PopulationBalanceError,
    ReselectException,
    bipartition_tree,
    bipartition_tree_random_with_num_cuts,
    find_balanced_edge_cuts_memoization,
    uniform_spanning_tree,
)
from ..tree.bipartition_tree import (
    FindBalancedEdgeCutsFn,
    _Cut,
    _PopulatedGraph,
)
from .proposals import ProposalFn


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
    subgraph_to_split: Graph | FrozenGraph,
    parts: Sequence[Hashable],
    pop_target: float | int,
    pop_col: str,
    epsilon: float,
    node_repeats: int = 0,
    bipartition_tree_fn: Callable[..., AbstractSet[Hashable]] = partial(
        bipartition_tree, max_attempts=100000
    ),
    *,
    rng: random.Random,
) -> dict[Hashable, Hashable]:
    """Bipartition a tree into two :math:`\\varepsilon`-balanced parts.

    Args:
        subgraph_to_split (Graph | FrozenGraph): The graph to partition into two
            :math:`\\varepsilon`-balanced parts.
        parts (Sequence): Iterable of part (district) labels (like ``[0,1,2]`` or ``range(4)``).
        pop_target (float | int): Target population for each part of the partition.
        pop_col (str): Node attribute key holding population data.
        epsilon (float): How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
            of the partition can be.
        node_repeats (int, optional): Additional roots to try on each spanning tree before
            drawing a new tree. Defaults to 0.
        bipartition_tree_fn (Callable, optional): The partition method to use. Defaults to
            ``partial(bipartition_tree, max_attempts=100000)``.
        rng (random.Random): The RNG supplied by the owning operation.

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
        rng=rng,
    )

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


PairSelection = Literal["district_pairs", "cut_edges"]


def _candidate_district_pairs(
    partition: Partition,
    pair_selection: PairSelection,
    rng: random.Random,
) -> Iterable[tuple[Hashable, Hashable]]:
    """Return the adjacent district pairs to try merging, in try order.

    With ``"district_pairs"`` each adjacent pair appears once, so the first pair is drawn uniformly
    from the adjacent district pairs. With ``"cut_edges"`` a pair's chance of coming first is
    proportional to the number of cut edges the two districts share, matching a uniform draw over
    the cut edges. Later entries are fallbacks, tried only if bipartitioning the earlier pairs
    fails; the ``"cut_edges"`` draws are lazy, so a successful first pair costs a single draw.
    """
    if pair_selection not in ("district_pairs", "cut_edges"):
        raise ValueError(
            f"Unknown pair_selection {pair_selection!r}; expected 'district_pairs' or 'cut_edges'."
        )

    part_order = {part: index for index, part in enumerate(partition.parts)}

    def normalized_pair(edge: tuple[Hashable, Hashable]) -> tuple[Hashable, Hashable]:
        pair = [partition.assignment.mapping[edge[0]], partition.assignment.mapping[edge[1]]]
        # Need to sort the pair so that the order is consistent
        pair.sort(key=part_order.__getitem__)
        return (pair[0], pair[1])

    def pair_sort_key(pair: tuple[Hashable, Hashable]) -> tuple[int, int]:
        return (part_order[pair[0]], part_order[pair[1]])

    if pair_selection == "district_pairs":
        # Sorted so the order does not depend on string-hash iteration order (PYTHONHASHSEED).
        pairs = sorted(
            {normalized_pair(edge) for edge in partition["cut_edges"]}, key=pair_sort_key
        )
        rng.shuffle(pairs)
        return pairs

    # "cut_edges": weight each adjacent pair by the number of cut edges it shares. Counting keeps
    # the per-edge work to one dict update, with sorting and drawing over the (much smaller) set
    # of adjacent pairs.
    counts: dict[tuple[Hashable, Hashable], int] = {}
    for edge in partition["cut_edges"]:
        pair = normalized_pair(edge)
        counts[pair] = counts.get(pair, 0) + 1
    # Sorted so the order does not depend on string-hash iteration order (PYTHONHASHSEED).
    pairs = sorted(counts, key=pair_sort_key)
    weights = [counts[pair] for pair in pairs]

    def draw_without_replacement() -> Iterator[tuple[Hashable, Hashable]]:
        while pairs:
            index = rng.choices(range(len(pairs)), weights=weights)[0]
            weights.pop(index)
            yield pairs.pop(index)

    return draw_without_replacement()


def recom(
    partition: Partition,
    pop_col: str,
    pop_target: int | float,
    epsilon: float,
    node_repeats: int = 0,
    region_surcharge: dict[str, float] | None = None,
    bipartition_tree_fn: Callable[..., AbstractSet[Hashable]] = bipartition_tree,
    pair_selection: PairSelection = "district_pairs",
    *,
    rng: random.Random | int | None = None,
) -> Partition:
    """Return new partition resulting from the ReCom algorithm.

    ReCom (short for ReCombination) is a Markov Chain Monte Carlo (MCMC) algorithm used for
    redistricting. At each step of the algorithm, a pair of adjacent districts is selected at
    random and merged into a single district. The region is then split into two new districts by
    generating a spanning tree using the Kruskal/Karger algorithm and cutting an edge at random.
    The edge is checked to ensure that it separates the region into two new districts that are
    population balanced, and, if not, a new edge is selected at random and the process is repeated.

    Example usage:

        from functools import partial
        from gerrychain import MarkovChain
        from gerrychain.proposals import recom

        # ...define constraints, accept, partition, total_steps here...

        # Ideal population: pop_target = sum(partition["population"].values()) / len(partition)

        proposal = partial(recom, pop_col="POP10", pop_target=pop_target, epsilon=.05)

        chain = MarkovChain(proposal, constraints, accept, partition, total_steps)

    Args:
        partition (Partition): The initial partition.
        pop_col (str): The name of the population column.
        pop_target (int | float): The target population for each district.
        epsilon (float): The epsilon value for population deviation as a percentage of the target
            population.
        node_repeats (int, optional): Additional roots to try on each spanning tree before
            drawing a new tree. Defaults to 0. Positive values are useful with contraction or
            custom cut-edge finders, but not with the default memoized finder.
        region_surcharge (dict | None, optional): The surcharge dictionary for the graph used
            for region-aware partitioning of the grid. Default is None.
        bipartition_tree_fn (Callable, optional): The method used for bipartitioning the tree.
            Default is `gerrychain.tree.bipartition_tree`. To configure the bipartition or
            spanning-tree step (e.g. ``max_attempts``, or ``spanning_tree_fn_kwargs`` for
            spanning-tree options), pass a pre-bound function, e.g.
            ``partial(bipartition_tree, spanning_tree_fn_kwargs={...})``.
        pair_selection ("district_pairs" | "cut_edges", optional): How to choose the pair of
            adjacent districts to merge. ``"district_pairs"`` (default) draws uniformly among
            the adjacent district pairs; ``"cut_edges"`` draws uniformly among the cut edges,
            so a pair's chance is proportional to the number of cut edges the two districts
            share.
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Partition: The new partition resulting from the ReCom algorithm.
    """

    rng = make_rng(rng)

    candidate_pairs = _candidate_district_pairs(partition, pair_selection, rng)

    # Bind region_surcharge onto the bipartition_tree_fn. Other bipartition / spanning-tree options
    # (e.g. spanning_tree_fn_kwargs) are configured by passing a pre-bound bipartition_tree_fn, such
    # as partial(bipartition_tree, spanning_tree_fn_kwargs={...}).
    bipartition_tree_fn = partial(bipartition_tree_fn, region_surcharge=region_surcharge)

    flips = None

    # Find a pair of touching "parts" that can be successfully bipartitioned into
    # two new "parts"
    #
    for parts_to_merge in candidate_pairs:
        try:
            subgraph_nodes = partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]

            flips = epsilon_tree_bipartition(
                partition.graph.subgraph(subgraph_nodes),
                parts_to_merge,
                pop_col=pop_col,
                pop_target=pop_target,
                epsilon=epsilon,
                node_repeats=node_repeats,
                bipartition_tree_fn=bipartition_tree_fn,
                rng=rng,
            )
            break

        except ReselectException:
            # Try again with a different pair of touching districts
            continue

    if flips is None:
        raise MetagraphError(
            "Bipartitioning failed for all adjacent district pairs reachable from cut edges."
        )

    return partition.flip(flips)


# Define a ProposalFn version to make purpose of the function clear
def build_recom_proposal_fn(
    pop_col: str,
    pop_target: int | float,
    epsilon: float,
    node_repeats: int = 0,
    region_surcharge: dict[str, float] | None = None,
    bipartition_tree_fn: Callable[..., AbstractSet[Hashable]] = bipartition_tree,
    pair_selection: PairSelection = "district_pairs",
) -> ProposalFn:
    proposal_fn = partial(
        recom,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        region_surcharge=region_surcharge,
        bipartition_tree_fn=bipartition_tree_fn,
        pair_selection=pair_selection,
    )
    return cast(ProposalFn, proposal_fn)


def reversible_recom(
    partition: Partition,
    pop_col: str,
    pop_target: int | float,
    epsilon: float,
    max_balanced_edge_cuts: int,
    find_balanced_edge_cuts_fn: FindBalancedEdgeCutsFn = find_balanced_edge_cuts_memoization,
    repeat_until_valid: bool = False,
    *,
    rng: random.Random | int | None = None,
) -> Partition:
    """Reversible ReCom algorithm for redistricting.

    This function performs the reversible ReCom algorithm, which is a Markov Chain Monte Carlo
    (MCMC) algorithm used for redistricting. For more information, see the paper "Spanning Tree
    Methods for Sampling Graph Partitions" by Cannon, et al. (2022) at
    https://arxiv.org/abs/2210.01401

    Args:
        partition (Partition): The initial partition.
        pop_col (str): The name of the population column.
        pop_target (int | float): The target population for each district.
        epsilon (float): The epsilon value for population deviation as a percentage of the target
            population.
        max_balanced_edge_cuts (int): The number of balanced edge cuts to draw from the spanning
            tree before selecting one, used to make the proposal reversible.
        find_balanced_edge_cuts_fn (Callable, optional): The balance edge function. Default is
            find_balanced_edge_cuts_memoization.
        repeat_until_valid (bool, optional): Flag indicating whether to repeat until a valid
            partition is found. Default is False.
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Partition: The new partition resulting from the reversible ReCom algorithm.
    """

    rng = make_rng(rng)

    def dist_pair_edges(
        part: Partition, a: Hashable, b: Hashable
    ) -> list[tuple[Hashable, Hashable]]:
        # frm: Find all edges that cross from district a into district b
        return [
            e
            for e in part.graph.edges
            if (
                (part.assignment.mapping[e[0]] == a and part.assignment.mapping[e[1]] == b)
                or (part.assignment.mapping[e[0]] == b and part.assignment.mapping[e[1]] == a)
            )
        ]

    def _bounded_find_balanced_edge_cuts_fn(
        h: _PopulatedGraph,
        one_sided_cut: bool = False,
        rootnode_choice_fn: Callable[[Sequence[Hashable]], Hashable] | None = None,
        *,
        rng: random.Random,
    ) -> list[_Cut]:
        if rootnode_choice_fn is None:
            rootnode_choice_fn = rng.choice
        cuts = find_balanced_edge_cuts_fn(
            h,
            one_sided_cut=one_sided_cut,
            rootnode_choice_fn=rootnode_choice_fn,
            rng=rng,
        )
        if len(cuts) > max_balanced_edge_cuts:
            raise ReversibilityError(
                f"Found {len(cuts)} balance edges, but the upper bound is {max_balanced_edge_cuts}."
            )
        return cuts

    parts = list(partition.parts)
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

    random_pair = rng.choice(dist_pairs)
    pair_edges = dist_pair_edges(partition, *random_pair)
    if random_pair[0] == random_pair[1] or not pair_edges:
        return partition  # self-loop: no adjacency

    # Note that Reversible ReCom targets the spanning tree distribution.
    # By modifying how the acceptance of partituclar partitioning
    # schemes is handled, we are able to sample exactly from that distribution
    # rather than an approximation of it like we do in regular ReCom.

    edge = rng.choice(pair_edges)
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
        find_balanced_edge_cuts_fn=_bounded_find_balanced_edge_cuts_fn,
        rng=rng,
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

    prob = num_possible_districts / (max_balanced_edge_cuts * seam_length)
    if prob > 1:
        raise ReversibilityError(
            f"Found {len(result) if result is not None else 0} balance edges, but "
            f"the upper bound (with seam length 1) is {max_balanced_edge_cuts}."
        )
    if rng.random() < prob:
        return new_part

    return partition  # self-loop


# Define a ProposalFn version to make purpose of the function clear
def build_reversible_recom_proposal_fn(
    pop_col: str,
    pop_target: int | float,
    epsilon: float,
    max_balanced_edge_cuts: int,
    find_balanced_edge_cuts_fn: FindBalancedEdgeCutsFn = find_balanced_edge_cuts_memoization,
    repeat_until_valid: bool = False,
) -> ProposalFn:
    proposal_fn = partial(
        reversible_recom,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        max_balanced_edge_cuts=max_balanced_edge_cuts,
        find_balanced_edge_cuts_fn=find_balanced_edge_cuts_fn,
        repeat_until_valid=repeat_until_valid,
    )
    return cast(ProposalFn, proposal_fn)


class ReCom:
    """Ready-made builders for the standard ReCom proposal variants.

    Each method returns a proposal function ready to hand to :class:`~gerrychain.MarkovChain`, so
    instead of the ``functools.partial`` incantation::

        from functools import partial
        proposal = partial(recom, pop_col="TOTPOP", pop_target=ideal_pop, epsilon=0.01)

    you can write::

        proposal = ReCom.district_pairs_mst(pop_col="TOTPOP", pop_target=ideal_pop, epsilon=0.01)

    This class is a namespace, not a type: it cannot be instantiated.

    The variants differ along two axes:

    * **Pair selection**: ``cut_edges_*`` picks a cut edge uniformly at random and merges the two
      districts on either side of it, so a pair's chance is proportional to the number of cut edges
      the districts share. ``district_pairs_*`` picks uniformly among the adjacent district pairs
      themselves.
    * **Spanning tree**: ``*_mst`` draws a minimum spanning tree on random edge weights using
      Kruskal's algorithm. ``*_ust`` draws a uniform spanning tree using Wilson's algorithm.

    :meth:`reversible` is the Reversible ReCom proposal, which samples exactly from the
    spanning-tree distribution; see :func:`reversible_recom`.

    The aliases ``A``, ``B``, ``C``, ``D``, and ``R`` name the same builders after the variants in
    "Spanning Tree Methods for Sampling Graph Partitions" (Cannon et al., 2022,
    https://arxiv.org/abs/2210.01401), to ease replication of results from that paper.

    These builders expose only the most common options. For anything else (a custom bipartition or
    spanning-tree function, ``node_repeats``, ...), use :func:`build_recom_proposal_fn` or
    :func:`build_reversible_recom_proposal_fn`, which these methods wrap, or bind
    ``functools.partial(recom, ...)`` yourself.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError(
            "ReCom is not instantiable; use the builder methods, e.g. "
            "ReCom.district_pairs_mst(...) or ReCom.reversible(...)."
        )

    @staticmethod
    def cut_edges_mst(
        pop_col: str,
        pop_target: int | float,
        epsilon: float,
        region_surcharge: dict[str, float] | None = None,
        allow_pair_reselection: bool = False,
    ) -> ProposalFn:
        """ReCom variant A: cut-edges pair selection, minimum spanning tree.

        A cut edge is selected at random and the two districts on either side of it are merged. The
        merged region is split back into two districts by drawing a minimum spanning tree on random
        edge weights (Kruskal's algorithm) and finding a population-balanced cut.

        Args:
            pop_col (str): The name of the population column.
            pop_target (int | float): The target population for each district.
            epsilon (float): Allowed population deviation as a percentage of the target
                population.
            region_surcharge (dict | None, optional): Surcharge dictionary for region-aware
                chains; see :func:`~gerrychain.tree.random_spanning_tree`. Default is None.
            allow_pair_reselection (bool, optional): Whether to fall back to a cut edge between
                a different district pair if bipartitioning the merged pair fails. Default is
                False.

        Returns:
            ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
        """
        return build_recom_proposal_fn(
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            region_surcharge=region_surcharge,
            bipartition_tree_fn=partial(
                bipartition_tree,
                allow_pair_reselection=allow_pair_reselection,
            ),
            pair_selection="cut_edges",
        )

    @staticmethod
    def district_pairs_mst(
        pop_col: str,
        pop_target: int | float,
        epsilon: float,
        region_surcharge: dict[str, float] | None = None,
        allow_pair_reselection: bool = False,
    ) -> ProposalFn:
        """ReCom variant B: district-pairs pair selection, minimum spanning tree.

        A pair of adjacent districts is selected uniformly at random and merged. The merged region
        is split back into two districts by drawing a minimum spanning tree on random edge weights
        (Kruskal's algorithm) and finding a population-balanced cut.

        Args:
            pop_col (str): The name of the population column.
            pop_target (int | float): The target population for each district.
            epsilon (float): Allowed population deviation as a percentage of the target population.
            region_surcharge (dict | None, optional): Surcharge dictionary for region-aware chains;
                see :func:`~gerrychain.tree.random_spanning_tree`. Default is None.
            allow_pair_reselection (bool, optional): Whether to allow reselection of the same
                district pair if bipartitioning fails. Default is False.

        Returns:
            ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
        """
        return build_recom_proposal_fn(
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            region_surcharge=region_surcharge,
            bipartition_tree_fn=partial(
                bipartition_tree,
                allow_pair_reselection=allow_pair_reselection,
            ),
            pair_selection="district_pairs",
        )

    @staticmethod
    def cut_edges_ust(
        pop_col: str,
        pop_target: int | float,
        epsilon: float,
        allow_pair_reselection: bool = False,
    ) -> ProposalFn:
        """ReCom variant C: cut-edges pair selection, uniform spanning tree.

        Like :meth:`cut_edges_mst`, except the merged region is split using a spanning tree drawn
        uniformly at random (Wilson's algorithm). Region surcharges are not supported: a uniform
        spanning tree ignores edge weights.

        Args:
            pop_col (str): The name of the population column.
            pop_target (int | float): The target population for each district.
            epsilon (float): Allowed population deviation as a percentage of the target
                population.
            allow_pair_reselection (bool, optional): Whether to fall back to a cut edge between
                a different district pair if bipartitioning the merged pair fails. Default is
                False.

        Returns:
            ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
        """
        return build_recom_proposal_fn(
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            pair_selection="cut_edges",
            bipartition_tree_fn=partial(
                bipartition_tree,
                spanning_tree_fn=uniform_spanning_tree,
                allow_pair_reselection=allow_pair_reselection,
            ),
        )

    @staticmethod
    def district_pairs_ust(
        pop_col: str,
        pop_target: int | float,
        epsilon: float,
        allow_pair_reselection: bool = False,
    ) -> ProposalFn:
        """ReCom variant D: district-pairs pair selection, uniform spanning tree.

        Like :meth:`district_pairs_mst`, except the merged region is split using a spanning
        tree drawn uniformly at random (Wilson's algorithm). Region surcharges are not
        supported: a uniform spanning tree ignores edge weights.

        Args:
            pop_col (str): The name of the population column.
            pop_target (int | float): The target population for each district.
            epsilon (float): Allowed population deviation as a percentage of the target population.
            allow_pair_reselection (bool, optional): Whether to allow reselection of the same
                district pair if bipartitioning fails. Default is False.

        Returns:
            ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
        """
        return build_recom_proposal_fn(
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            pair_selection="district_pairs",
            bipartition_tree_fn=partial(
                bipartition_tree,
                spanning_tree_fn=uniform_spanning_tree,
                allow_pair_reselection=allow_pair_reselection,
            ),
        )

    @staticmethod
    def reversible(
        pop_col: str,
        pop_target: int | float,
        epsilon: float,
        max_balanced_edge_cuts: int,
        repeat_until_valid: bool = False,
    ) -> ProposalFn:
        """ReCom variant R: the reversible ReCom proposal.

        Samples exactly from the spanning-tree distribution rather than an approximation of it; see
        :func:`reversible_recom` and the paper "Spanning Tree Methods for Sampling Graph Partitions"
        (https://arxiv.org/abs/2210.01401) for details.

        Args:
            pop_col (str): The name of the population column.
            pop_target (int | float): The target population for each district.
            epsilon (float): Allowed population deviation as a percentage of the target
                population.
            max_balanced_edge_cuts (int): The number of balanced edge cuts to draw from the
                spanning tree before selecting one, used to make the proposal reversible.
            repeat_until_valid (bool, optional): Whether to repeat until a valid partition is
                found. Default is False.

        Returns:
            ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
        """
        return build_reversible_recom_proposal_fn(
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            max_balanced_edge_cuts=max_balanced_edge_cuts,
            repeat_until_valid=repeat_until_valid,
        )

    # Variant names from "Spanning Tree Methods for Sampling Graph Partitions".
    A = cut_edges_mst
    B = district_pairs_mst
    C = cut_edges_ust
    D = district_pairs_ust
    R = reversible


class ReversibilityError(Exception):
    """Raised when the cut edge upper bound is violated."""

    def __init__(self, msg: str) -> None:
        self.message = msg
