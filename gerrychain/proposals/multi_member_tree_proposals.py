import math
import random
from collections.abc import Hashable, Mapping, Sequence
from functools import partial
from numbers import Integral
from typing import cast


from gerrychain._rng import make_rng
from gerrychain.partition import Partition

from ..graph import FrozenGraph, Graph
from ..tree import (
    PopulationBalanceError,
    ReselectException,
    bipartition_tree,
    uniform_spanning_tree,
)
from ..tree.bipartition_tree import (
    BipartitionTreeFn,
    ReComBipartitionTreeFn,
)
from .proposals import ProposalFn
from .tree_proposals import (
    PairSelection,
    _candidate_district_pairs,
    MetagraphError,
)


def _validate_multi_member_config(
    members_per_district: Mapping[Hashable, int],
    pop_target: int | float,
    epsilon: float,
) -> dict[Hashable, int]:
    if not members_per_district:
        raise ValueError("members_per_district must not be empty.")
    if pop_target <= 0 or (isinstance(pop_target, float) and not math.isfinite(pop_target)):
        raise ValueError(f"pop_target must be finite and positive; got {pop_target!r}.")
    if not 0 <= epsilon < 1:
        raise ValueError(f"epsilon must satisfy 0 <= epsilon < 1; got {epsilon!r}.")

    members: dict[Hashable, int] = {}
    for part, member_count in members_per_district.items():
        if (
            isinstance(member_count, bool)
            or not isinstance(member_count, Integral)
            or member_count <= 0
        ):
            raise ValueError(
                f"Member count for district {part!r} must be a positive integer; "
                f"got {member_count!r}."
            )
        members[part] = int(member_count)
    return members


def epsilon_tree_bipartition_multi_member(
    subgraph_to_split: Graph | FrozenGraph,
    parts: Sequence[Hashable],
    pop_target_by_part: Mapping[Hashable, int | float],
    pop_col: str,
    epsilon: float,
    node_repeats: int = 0,
    bipartition_tree_fn: BipartitionTreeFn = partial(bipartition_tree, max_attempts=100000),
    *,
    rng: random.Random,
) -> dict[Hashable, Hashable]:
    """Bipartition a merged pair using a separate population target for each label.

    Args:
        subgraph_to_split (Graph | FrozenGraph): The merged district graph to split.
        parts (Sequence[Hashable]): The two district labels receiving the resulting sides.
        pop_target_by_part (Mapping[Hashable, int | float]): Population target for each label.
        pop_col (str): Node attribute key holding population data.
        epsilon (float): Allowed deviation from each district's own target.
        node_repeats (int, optional): Additional roots to try per spanning tree. Defaults to 0.
        bipartition_tree_fn (BipartitionTreeFn, optional): Tree bipartition function.
        rng (random.Random): The RNG supplied by the owning operation.

    Returns:
        dict[Hashable, Hashable]: New assignments in the parent graph's node ID space.
    """
    if len(parts) != 2:
        raise ValueError("This function requires exactly two part labels.")

    missing = [part for part in parts if part not in pop_target_by_part]
    if missing:
        raise ValueError(f"pop_target_by_part is missing targets for labels {missing!r}.")

    part_a, part_b = parts
    target_a = pop_target_by_part[part_a]
    target_b = pop_target_by_part[part_b]
    remaining_nodes = subgraph_to_split.node_indices
    total_population = sum(subgraph_to_split.node_data(node)[pop_col] for node in remaining_nodes)

    lower = max(
        target_a * (1 - epsilon),
        total_population - target_b * (1 + epsilon),
    )
    upper = min(
        target_a * (1 + epsilon),
        total_population - target_b * (1 - epsilon),
    )
    if lower > upper:
        raise PopulationBalanceError(
            f"No feasible population interval for parts {part_a!r} and {part_b!r}: "
            f"targets=({target_a!r}, {target_b!r}), "
            f"merged_population={total_population!r}, epsilon={epsilon!r}."
        )

    cut_target = (lower + upper) / 2
    cut_epsilon = (upper - lower) / (2 * cut_target)
    nodes = bipartition_tree_fn(
        subgraph_to_split.subgraph(remaining_nodes),
        pop_col=pop_col,
        pop_target=cut_target,
        epsilon=cut_epsilon,
        node_repeats=node_repeats,
        one_sided_cut=True,
        rng=rng,
    )

    flips = {node: part_a for node in nodes}
    selected_population = sum(subgraph_to_split.node_data(node)[pop_col] for node in nodes)

    # NOTE: Population checks are defensive. This should never trigger if starting from a valid seed
    if not target_a * (1 - epsilon) <= selected_population <= target_a * (1 + epsilon):
        raise PopulationBalanceError(
            f"Population {selected_population!r} assigned to part {part_a!r} is outside "
            f"target {target_a!r} with epsilon {epsilon!r}."
        )

    remaining_nodes -= nodes
    for node in remaining_nodes:
        flips[node] = part_b
    remaining_population = total_population - selected_population
    if not target_b * (1 - epsilon) <= remaining_population <= target_b * (1 + epsilon):
        raise PopulationBalanceError(
            f"Population {remaining_population!r} assigned to part {part_b!r} is outside "
            f"target {target_b!r} with epsilon {epsilon!r}."
        )

    return subgraph_to_split.translate_subgraph_node_ids_for_flips(flips)


def multi_member_recom(
    partition: Partition,
    pop_col: str,
    pop_target: int | float,
    epsilon: float,
    members_per_district: Mapping[Hashable, int],
    node_repeats: int = 0,
    region_surcharge: dict[str, float] | None = None,
    bipartition_tree_fn: ReComBipartitionTreeFn = bipartition_tree,
    pair_selection: PairSelection = "district_pairs",
    *,
    rng: random.Random | int | None = None,
) -> Partition:
    """Return a ReCom proposal for districts with fixed, unequal member counts.

    ``pop_target`` is the target population for one member. Each district's target is
    ``pop_target * members_per_district[label]``. Member counts remain attached to district labels
    while ReCom changes their geography.

    Args:
        partition (Partition): The current partition.
        pop_col (str): The name of the population column.
        pop_target (int | float): Target population for one member.
        epsilon (float): Allowed deviation from each district's own target. Must be in ``[0, 1)``.
        members_per_district (Mapping[Hashable, int]): Positive member count for every district.
        node_repeats (int, optional): Additional roots to try per spanning tree. Defaults to 0.
        region_surcharge (dict | None, optional): Surcharges for region-aware spanning trees.
        bipartition_tree_fn (ReComBipartitionTreeFn, optional): Tree bipartition function.
        pair_selection ("district_pairs" | "cut_edges", optional): Adjacent-pair selection mode.
        rng (random.Random | int | None, optional): Source of randomness.

    Returns:
        Partition: The proposed partition.
    """
    members = _validate_multi_member_config(members_per_district, pop_target, epsilon)
    missing = [part for part in partition.parts if part not in members]
    unexpected = [part for part in members if part not in partition.parts]
    if missing or unexpected:
        raise ValueError(
            "members_per_district keys must match the partition labels exactly; "
            f"missing={missing!r}, unexpected={unexpected!r}."
        )

    rng = make_rng(rng)
    candidate_pairs = _candidate_district_pairs(partition, pair_selection, rng)
    bipartition_tree_fn = cast(
        ReComBipartitionTreeFn,
        partial(bipartition_tree_fn, region_surcharge=region_surcharge),
    )

    flips = None
    for parts_to_merge in candidate_pairs:
        try:
            subgraph_nodes = partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
            pop_target_by_part = {part: pop_target * members[part] for part in parts_to_merge}
            flips = epsilon_tree_bipartition_multi_member(
                partition.graph.subgraph(subgraph_nodes),
                parts_to_merge,
                pop_target_by_part=pop_target_by_part,
                pop_col=pop_col,
                epsilon=epsilon,
                node_repeats=node_repeats,
                bipartition_tree_fn=bipartition_tree_fn,
                rng=rng,
            )
            break
        except ReselectException:
            continue

    if flips is None:
        raise MetagraphError(
            "Bipartitioning failed for all adjacent district pairs reachable from cut edges."
        )

    return partition.flip(flips)


def build_multi_member_recom_proposal_fn(
    pop_col: str,
    pop_target: int | float,
    epsilon: float,
    members_per_district: Mapping[Hashable, int],
    node_repeats: int = 0,
    region_surcharge: dict[str, float] | None = None,
    bipartition_tree_fn: ReComBipartitionTreeFn = bipartition_tree,
    pair_selection: PairSelection = "district_pairs",
) -> ProposalFn:
    """Build a multi-member ReCom proposal with fixed member counts by district label.

    Args:
        pop_col (str): The name of the population column.
        pop_target (int | float): Target population for one member.
        epsilon (float): Allowed deviation from each district's own target. Must be in ``[0, 1)``.
        members_per_district (Mapping[Hashable, int]): Positive member count for every district.
        node_repeats (int, optional): Additional roots to try per spanning tree. Defaults to 0.
        region_surcharge (dict | None, optional): Surcharges for region-aware spanning trees.
        bipartition_tree_fn (ReComBipartitionTreeFn, optional): Tree bipartition function.
        pair_selection ("district_pairs" | "cut_edges", optional): Adjacent-pair selection mode.

    Returns:
        ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
    """
    members = _validate_multi_member_config(members_per_district, pop_target, epsilon)
    proposal_fn = partial(
        multi_member_recom,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        members_per_district=members,
        node_repeats=node_repeats,
        region_surcharge=region_surcharge,
        bipartition_tree_fn=bipartition_tree_fn,
        pair_selection=pair_selection,
    )
    return cast(ProposalFn, proposal_fn)


class MultiMemberReCom:
    """Ready-made builders for ReCom with fixed member counts by district label.

    The methods mirror the four non-reversible :class:`ReCom` variants. They use a target
    population per member and do not provide reversible or letter-named variants. This class is a
    namespace and cannot be instantiated.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError(
            "MultiMemberReCom is not instantiable; use a builder method, e.g. "
            "MultiMemberReCom.district_pairs_mst(...)."
        )

    @staticmethod
    def cut_edges_mst(
        pop_col: str,
        pop_target: int | float,
        epsilon: float,
        members_per_district: Mapping[Hashable, int],
        region_surcharge: dict[str, float] | None = None,
        allow_pair_reselection: bool = False,
    ) -> ProposalFn:
        """Build multi-member ReCom with cut-edge pair selection and a minimum spanning tree.

        A cut edge is selected uniformly at random, so district pairs are weighted by the number of
        boundary edges they share. The merged pair is split using a minimum spanning tree on random
        edge weights. Each district's target population is ``pop_target`` multiplied by its fixed
        member count in ``members_per_district``.

        Args:
            pop_col (str): Node attribute containing population data.
            pop_target (int | float): Target population for one elected member.
            epsilon (float): Allowed deviation from each district's member-adjusted target. Must be
                in ``[0, 1)``.
            members_per_district (Mapping[Hashable, int]): Positive member count for every district
                label. Member counts remain attached to these labels throughout the chain.
            region_surcharge (dict[str, float] | None, optional): Surcharges used to discourage the
                spanning tree from crossing specified region boundaries. Defaults to ``None``.
            allow_pair_reselection (bool, optional): Whether to try a different adjacent district
                pair when tree splitting fails for the selected pair. Defaults to ``False``.

        Returns:
            ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
        """
        return build_multi_member_recom_proposal_fn(
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            members_per_district=members_per_district,
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
        members_per_district: Mapping[Hashable, int],
        region_surcharge: dict[str, float] | None = None,
        allow_pair_reselection: bool = False,
    ) -> ProposalFn:
        """Build multi-member ReCom with district-pair selection and a minimum spanning tree.

        An adjacent district pair is selected uniformly, independent of shared boundary length and
        member count. The merged pair is split using a minimum spanning tree on random edge weights.
        Each district's target population is ``pop_target`` multiplied by its fixed member count in
        ``members_per_district``.

        Args:
            pop_col (str): Node attribute containing population data.
            pop_target (int | float): Target population for one elected member.
            epsilon (float): Allowed deviation from each district's member-adjusted target. Must be
                in ``[0, 1)``.
            members_per_district (Mapping[Hashable, int]): Positive member count for every district
                label. Member counts remain attached to these labels throughout the chain.
            region_surcharge (dict[str, float] | None, optional): Surcharges used to discourage the
                spanning tree from crossing specified region boundaries. Defaults to ``None``.
            allow_pair_reselection (bool, optional): Whether to try a different adjacent district
                pair when tree splitting fails for the selected pair. Defaults to ``False``.

        Returns:
            ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
        """
        return build_multi_member_recom_proposal_fn(
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            members_per_district=members_per_district,
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
        members_per_district: Mapping[Hashable, int],
        allow_pair_reselection: bool = False,
    ) -> ProposalFn:
        """Build multi-member ReCom with cut-edge pair selection and a uniform spanning tree.

        A cut edge is selected uniformly at random, so district pairs are weighted by the number of
        boundary edges they share. The merged pair is split using a spanning tree drawn uniformly
        with Wilson's algorithm. Each district's target population is ``pop_target`` multiplied by
        its fixed member count in ``members_per_district``. Region surcharges are not supported
        because a uniform spanning tree does not use edge weights.

        Args:
            pop_col (str): Node attribute containing population data.
            pop_target (int | float): Target population for one elected member.
            epsilon (float): Allowed deviation from each district's member-adjusted target. Must be
                in ``[0, 1)``.
            members_per_district (Mapping[Hashable, int]): Positive member count for every district
                label. Member counts remain attached to these labels throughout the chain.
            allow_pair_reselection (bool, optional): Whether to try a different adjacent district
                pair when tree splitting fails for the selected pair. Defaults to ``False``.

        Returns:
            ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
        """
        return build_multi_member_recom_proposal_fn(
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            members_per_district=members_per_district,
            bipartition_tree_fn=partial(
                bipartition_tree,
                spanning_tree_fn=uniform_spanning_tree,
                allow_pair_reselection=allow_pair_reselection,
            ),
            pair_selection="cut_edges",
        )

    @staticmethod
    def district_pairs_ust(
        pop_col: str,
        pop_target: int | float,
        epsilon: float,
        members_per_district: Mapping[Hashable, int],
        allow_pair_reselection: bool = False,
    ) -> ProposalFn:
        """Build multi-member ReCom with district-pair selection and a uniform spanning tree.

        An adjacent district pair is selected uniformly, independent of shared boundary length and
        member count. The merged pair is split using a spanning tree drawn uniformly with Wilson's
        algorithm. Each district's target population is ``pop_target`` multiplied by its fixed
        member count in ``members_per_district``. Region surcharges are not supported because a
        uniform spanning tree does not use edge weights.

        Args:
            pop_col (str): Node attribute containing population data.
            pop_target (int | float): Target population for one elected member.
            epsilon (float): Allowed deviation from each district's member-adjusted target. Must be
                in ``[0, 1)``.
            members_per_district (Mapping[Hashable, int]): Positive member count for every district
                label. Member counts remain attached to these labels throughout the chain.
            allow_pair_reselection (bool, optional): Whether to try a different adjacent district
                pair when tree splitting fails for the selected pair. Defaults to ``False``.

        Returns:
            ProposalFn: A proposal function for use with :class:`~gerrychain.MarkovChain`.
        """
        return build_multi_member_recom_proposal_fn(
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            members_per_district=members_per_district,
            bipartition_tree_fn=partial(
                bipartition_tree,
                spanning_tree_fn=uniform_spanning_tree,
                allow_pair_reselection=allow_pair_reselection,
            ),
            pair_selection="district_pairs",
        )

    A = cut_edges_mst
    B = district_pairs_mst
    C = cut_edges_ust
    D = district_pairs_ust
