import random
from collections.abc import Callable, Hashable, Mapping, Sequence
from functools import partial
from typing import AbstractSet, Any, cast

import networkx as nx
import pytest

from gerrychain import Graph, Partition, proposals, updaters
from gerrychain.graph import FrozenGraph
from gerrychain.proposals import ProposalFn
from gerrychain.proposals.multi_member_tree_proposals import (
    epsilon_tree_bipartition_multi_member,
)
from gerrychain.proposals.tree_proposals import PairSelection
from gerrychain.tree import (
    PopulationBalanceError,
    ReselectException,
    bipartition_tree,
    uniform_spanning_tree,
)


def make_path_partition(part_sizes: Sequence[int], labels: Sequence[Hashable]) -> Partition:
    graph = nx.path_graph(sum(part_sizes))
    nx.set_node_attributes(graph, {node: 1 for node in graph}, "population")
    nx.set_node_attributes(
        graph,
        {node: "left" if node < len(graph) / 2 else "right" for node in graph},
        "region",
    )
    assignment = {}
    start = 0
    for label, size in zip(labels, part_sizes):
        assignment.update({node: label for node in range(start, start + size)})
        start += size
    return Partition(
        graph,
        assignment,
        {
            "cut_edges": updaters.cut_edges,
            "population": updaters.Tally("population"),
        },
    )


@pytest.fixture
def partition(graph: Graph) -> Partition:
    return Partition(
        graph,
        {0: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3},
        {
            "cut_edges": updaters.cut_edges,
            "cut_edges_by_part": updaters.cut_edges_by_part,
        },
    )


@pytest.mark.parametrize(
    "proposal",
    [
        proposals.propose_any_node_flip,
        proposals.propose_flip_every_district,
        proposals.propose_chunk_flip,
        proposals.propose_random_flip,
        proposals.slow_reversible_propose,
        proposals.slow_reversible_propose_bi,
        proposals.spectral_recom,
        proposals.build_any_node_flip_proposal_fn(),
        proposals.build_flip_every_district_proposal_fn(),
        proposals.build_chunk_flip_proposal_fn(),
        proposals.build_random_flip_proposal_fn(),
        proposals.build_slow_reversible_proposal_fn(),
        proposals.build_slow_reversible_bi_proposal_fn(),
        proposals.build_spectral_recom_proposal_fn(),
    ],
)
def test_proposal_returns_a_partition(proposal: ProposalFn, partition: Partition):
    proposed = proposal(partition, rng=random.Random(0))
    assert isinstance(proposed, partition.__class__)


def test_proposals_support_mixed_type_part_labels(graph: Graph):
    for node in graph:
        graph.node_data(node)["population"] = 1
    partition = Partition(
        graph,
        {0: 1, 1: 1, 2: 1, 3: "a", 4: "a", 5: "a", 6: 2, 7: 2, 8: 2},
        {
            "cut_edges": updaters.cut_edges,
            "cut_edges_by_part": updaters.cut_edges_by_part,
            "population": updaters.Tally("population"),
        },
    )

    assert proposals.slow_reversible_propose(partition, rng=0)
    assert proposals.slow_reversible_propose_bi(partition, rng=0)
    assert proposals.recom(
        partition,
        pop_col="population",
        pop_target=3,
        epsilon=0,
        rng=0,
    )


@pytest.fixture
def populated_partition(graph: Graph) -> Partition:
    for node in graph:
        graph.node_data(node)["population"] = 1
    return Partition(
        graph,
        {0: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3},
        {
            "cut_edges": updaters.cut_edges,
            "population": updaters.Tally("population"),
        },
    )


def test_recom_namespace_is_not_instantiable():
    with pytest.raises(TypeError, match="not instantiable"):
        proposals.ReCom(pop_col="population", pop_target=3, epsilon=0)


def test_recom_letter_aliases_match_named_variants():
    assert proposals.ReCom.A is proposals.ReCom.cut_edges_mst
    assert proposals.ReCom.B is proposals.ReCom.district_pairs_mst
    assert proposals.ReCom.C is proposals.ReCom.cut_edges_ust
    assert proposals.ReCom.D is proposals.ReCom.district_pairs_ust
    assert proposals.ReCom.R is proposals.ReCom.reversible


@pytest.mark.parametrize(
    "build_proposal",
    [
        proposals.ReCom.cut_edges_mst,
        proposals.ReCom.district_pairs_mst,
        proposals.ReCom.cut_edges_ust,
        proposals.ReCom.district_pairs_ust,
    ],
)
def test_recom_variants_return_balanced_partitions(
    build_proposal: Callable[..., ProposalFn], populated_partition: Partition
):
    proposal = build_proposal(pop_col="population", pop_target=3, epsilon=0)
    proposed = proposal(populated_partition, rng=random.Random(0))
    assert isinstance(proposed, Partition)
    assert all(pop == 3 for pop in proposed["population"].values())


@pytest.mark.parametrize(
    "build_proposal",
    [
        proposals.ReCom.cut_edges_mst,
        proposals.ReCom.district_pairs_mst,
        proposals.ReCom.cut_edges_ust,
        proposals.ReCom.district_pairs_ust,
    ],
)
def test_recom_variants_run_with_pair_reselection(
    build_proposal: Callable[..., ProposalFn], populated_partition: Partition
):
    proposal = build_proposal(
        pop_col="population", pop_target=3, epsilon=0, allow_pair_reselection=True
    )
    proposed = proposal(populated_partition, rng=random.Random(0))
    assert isinstance(proposed, Partition)
    assert all(pop == 3 for pop in proposed["population"].values())


@pytest.mark.parametrize(
    "build_proposal, recom_kwargs",
    [
        (proposals.ReCom.cut_edges_mst, {"pair_selection": "cut_edges"}),
        (proposals.ReCom.district_pairs_mst, {"pair_selection": "district_pairs"}),
        (
            proposals.ReCom.cut_edges_ust,
            {
                "pair_selection": "cut_edges",
                "bipartition_tree_fn": partial(
                    bipartition_tree, spanning_tree_fn=uniform_spanning_tree
                ),
            },
        ),
        (
            proposals.ReCom.district_pairs_ust,
            {
                "pair_selection": "district_pairs",
                "bipartition_tree_fn": partial(
                    bipartition_tree, spanning_tree_fn=uniform_spanning_tree
                ),
            },
        ),
    ],
)
def test_recom_variants_match_direct_recom_calls(
    build_proposal: Callable[..., ProposalFn],
    recom_kwargs: dict[str, Any],
    populated_partition: Partition,
):
    """Pin each builder's wiring: same seed, same trajectory as recom with the bound options.

    A builder that binds the wrong pair_selection or forgets the uniform spanning tree consumes
    the RNG stream differently, so the assignments diverge.
    """
    proposal = build_proposal(pop_col="population", pop_target=3, epsilon=0)
    proposed = proposal(populated_partition, rng=random.Random(0))
    expected = proposals.recom(
        populated_partition,
        pop_col="population",
        pop_target=3,
        epsilon=0,
        rng=random.Random(0),
        **recom_kwargs,
    )
    assert proposed.assignment.mapping == expected.assignment.mapping


def test_reversible_variant_matches_direct_reversible_recom_call(populated_partition: Partition):
    proposal = proposals.ReCom.reversible(
        pop_col="population", pop_target=3, epsilon=0, max_balanced_edge_cuts=100
    )
    proposed = proposal(populated_partition, rng=random.Random(0))
    expected = proposals.reversible_recom(
        populated_partition,
        pop_col="population",
        pop_target=3,
        epsilon=0,
        max_balanced_edge_cuts=100,
        rng=random.Random(0),
    )
    assert proposed.assignment.mapping == expected.assignment.mapping


def test_recom_reversible_variant_runs(populated_partition: Partition):
    proposal = proposals.ReCom.reversible(
        pop_col="population", pop_target=3, epsilon=0, max_balanced_edge_cuts=100
    )
    proposed = proposal(populated_partition, rng=random.Random(0))
    assert isinstance(proposed, Partition)


def test_recom_rejects_unknown_pair_selection(populated_partition: Partition):
    with pytest.raises(ValueError, match="pair_selection"):
        proposals.recom(
            populated_partition,
            pop_col="population",
            pop_target=3,
            epsilon=0,
            pair_selection=cast(PairSelection, "nope"),
            rng=0,
        )


def test_cut_edges_pair_selection_weights_by_shared_boundary(graph: Graph):
    """District pairs sharing more cut edges should be tried first more often.

    On the 3x3 grid with districts a={0}, b={1,2}, c={3..8}, the pair (b,c) shares two cut
    edges (1-4 and 2-5) while (a,b) and (a,c) share one each (0-1 and 0-3). Under "cut_edges"
    selection (b,c) should come first about half the time; under "district_pairs" about a
    third of the time.
    """
    from gerrychain.proposals.tree_proposals import _candidate_district_pairs

    partition = Partition(
        graph,
        {0: "a", 1: "b", 2: "b", 3: "c", 4: "c", 5: "c", 6: "c", 7: "c", 8: "c"},
        {"cut_edges": updaters.cut_edges},
    )

    def count_bc_first(pair_selection: PairSelection) -> int:
        count = 0
        for seed in range(600):
            pairs = list(_candidate_district_pairs(partition, pair_selection, random.Random(seed)))
            assert sorted(pairs) == [("a", "b"), ("a", "c"), ("b", "c")]
            count += pairs[0] == ("b", "c")
        return count

    # Expected 300 of 600 for cut_edges, 200 of 600 for district_pairs.
    assert count_bc_first("cut_edges") > 260
    assert count_bc_first("district_pairs") < 240


def test_multi_member_recom_exact_two_to_one_split():
    partition = make_path_partition([6, 3], ["two", "one"])
    members: Mapping[Hashable, int] = {"two": 2, "one": 1}

    proposed = proposals.multi_member_recom(
        partition,
        pop_col="population",
        pop_target=3,
        epsilon=0,
        members_per_district=members,
        rng=0,
    )

    assert proposed["population"] == {"two": 6, "one": 3}


def test_multi_member_recom_three_to_two_split_with_epsilon():
    partition = make_path_partition([6, 4], ["three", "two"])
    members: Mapping[Hashable, int] = {"three": 3, "two": 2}

    proposed = proposals.multi_member_recom(
        partition,
        pop_col="population",
        pop_target=2,
        epsilon=0.25,
        members_per_district=members,
        rng=2,
    )

    for part, population in proposed["population"].items():
        target = 2 * members[part]
        assert target * 0.75 <= population <= target * 1.25


def test_multi_member_recom_preserves_per_label_bounds_across_steps():
    partition = make_path_partition([6, 3, 3], [1, "a", 3])
    members: dict[Hashable, int] = {1: 2, "a": 1, 3: 1}
    proposal = proposals.MultiMemberReCom.district_pairs_mst("population", 3, 0, members)
    rng = random.Random(11)

    for _ in range(8):
        partition = proposal(partition, rng=rng)
        assert partition["population"] == {1: 6, "a": 3, 3: 3}


def test_multi_member_recom_same_seed_produces_same_trajectory():
    members: dict[Hashable, int] = {1: 2, "a": 1, 3: 1}

    def trajectory(seed: int) -> list[dict[Hashable, Hashable]]:
        partition = make_path_partition([6, 3, 3], [1, "a", 3])
        proposal = proposals.build_multi_member_recom_proposal_fn("population", 3, 0, members)
        rng = random.Random(seed)
        assignments = []
        for _ in range(8):
            partition = proposal(partition, rng=rng)
            assignments.append(dict(partition.assignment.mapping))
        return assignments

    assert trajectory(4) == trajectory(4)


@pytest.mark.parametrize(
    "build_proposal, recom_kwargs",
    [
        (proposals.MultiMemberReCom.cut_edges_mst, {"pair_selection": "cut_edges"}),
        (
            proposals.MultiMemberReCom.district_pairs_mst,
            {"pair_selection": "district_pairs"},
        ),
        (
            proposals.MultiMemberReCom.cut_edges_ust,
            {
                "pair_selection": "cut_edges",
                "bipartition_tree_fn": partial(
                    bipartition_tree, spanning_tree_fn=uniform_spanning_tree
                ),
            },
        ),
        (
            proposals.MultiMemberReCom.district_pairs_ust,
            {
                "pair_selection": "district_pairs",
                "bipartition_tree_fn": partial(
                    bipartition_tree, spanning_tree_fn=uniform_spanning_tree
                ),
            },
        ),
    ],
)
def test_multi_member_recom_variants_match_direct_calls(
    build_proposal: Callable[..., ProposalFn], recom_kwargs: dict[str, Any]
):
    partition = make_path_partition([6, 3, 3], [1, "a", 3])
    members: dict[Hashable, int] = {1: 2, "a": 1, 3: 1}
    proposal = build_proposal("population", 3, 0, members)

    proposed = proposal(partition, rng=random.Random(7))
    expected = proposals.multi_member_recom(
        partition,
        pop_col="population",
        pop_target=3,
        epsilon=0,
        members_per_district=members,
        rng=random.Random(7),
        **recom_kwargs,
    )

    assert proposed.assignment.mapping == expected.assignment.mapping


def test_multi_member_recom_namespace_has_only_nonreversible_variants():
    with pytest.raises(TypeError, match="not instantiable"):
        proposals.MultiMemberReCom()

    for name in ("reversible", "R"):
        assert not hasattr(proposals.MultiMemberReCom, name)


def test_multi_member_recom_passes_region_surcharge_to_tree():
    partition = make_path_partition([6, 3], ["two", "one"])
    members: Mapping[Hashable, int] = {"two": 2, "one": 1}
    captured: list[dict[str, float] | None] = []

    def spy_bipartition_tree(
        subgraph: Graph | FrozenGraph,
        /,
        *,
        pop_col: str,
        pop_target: float,
        epsilon: float,
        node_repeats: int = 0,
        single_district_cut: bool = False,
        region_surcharge: dict[str, float] | None = None,
        rng: random.Random,
    ) -> AbstractSet[Hashable]:
        captured.append(region_surcharge)
        return bipartition_tree(
            subgraph,
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            node_repeats=node_repeats,
            single_district_cut=single_district_cut,
            region_surcharge=region_surcharge,
            rng=rng,
        )

    proposals.multi_member_recom(
        partition,
        pop_col="population",
        pop_target=3,
        epsilon=0,
        members_per_district=members,
        region_surcharge={"region": 1.5},
        bipartition_tree_fn=spy_bipartition_tree,
        rng=0,
    )

    assert captured == [{"region": 1.5}]


@pytest.mark.parametrize(
    "members, pop_target, epsilon, message",
    [
        ({}, 1, 0, "must not be empty"),
        ({1: True}, 1, 0, "positive integer"),
        ({1: 1.5}, 1, 0, "positive integer"),
        ({1: 0}, 1, 0, "positive integer"),
        ({1: -1}, 1, 0, "positive integer"),
        ({1: 1}, 0, 0, "pop_target"),
        ({1: 1}, float("nan"), 0, "pop_target"),
        ({1: 1}, float("inf"), 0, "pop_target"),
        ({1: 1}, float("-inf"), 0, "pop_target"),
        ({1: 1}, 1, -0.01, "epsilon"),
        ({1: 1}, 1, 1, "epsilon"),
    ],
)
def test_multi_member_recom_builder_rejects_invalid_configuration(
    members: Any,
    pop_target: int | float,
    epsilon: float,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        proposals.build_multi_member_recom_proposal_fn("population", pop_target, epsilon, members)


def test_multi_member_recom_reports_missing_and_unexpected_labels():
    partition = make_path_partition([6, 3], [1, "a"])

    with pytest.raises(ValueError, match=r"missing=\['a'\].*unexpected=\[3\]"):
        proposals.multi_member_recom(
            partition,
            "population",
            3,
            0,
            {1: 2, 3: 1},
            rng=0,
        )


def test_multi_member_recom_builder_copies_member_mapping():
    partition = make_path_partition([6, 3], ["two", "one"])
    members: dict[Hashable, int] = {"two": 2, "one": 1}
    proposal = proposals.build_multi_member_recom_proposal_fn("population", 3, 0, members)

    members["two"] = 1

    proposed = proposal(partition, rng=random.Random(0))
    assert proposed["population"] == {"two": 6, "one": 3}


def test_multi_member_recom_infeasible_pair_fails_without_reselection(
    monkeypatch: pytest.MonkeyPatch,
):
    from gerrychain.proposals import multi_member_tree_proposals

    partition = make_path_partition([7, 1, 4], [1, "a", 3])
    monkeypatch.setattr(
        multi_member_tree_proposals,
        "_candidate_district_pairs",
        lambda partition, pair_selection, rng: [(1, "a"), ("a", 3)],
    )

    with pytest.raises(PopulationBalanceError, match="No feasible population interval"):
        proposals.multi_member_recom(
            partition,
            "population",
            3,
            0,
            {1: 2, "a": 1, 3: 1},
            rng=0,
        )


def test_multi_member_bipartition_rejects_out_of_range_custom_cut():
    partition = make_path_partition([6, 3], ["two", "one"])
    merged = partition.graph.subgraph(partition.graph.node_indices)

    def empty_cut(
        subgraph: Graph | FrozenGraph,
        /,
        *,
        pop_col: str,
        pop_target: float,
        epsilon: float,
        node_repeats: int = 0,
        single_district_cut: bool = False,
        rng: random.Random,
    ) -> AbstractSet[Hashable]:
        return frozenset()

    with pytest.raises(PopulationBalanceError, match="assigned to part 'two'"):
        epsilon_tree_bipartition_multi_member(
            merged,
            ["two", "one"],
            {"two": 6, "one": 3},
            "population",
            0,
            bipartition_tree_fn=empty_cut,
            rng=random.Random(0),
        )


def test_multi_member_recom_reselects_after_tree_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    from gerrychain.proposals import multi_member_tree_proposals

    partition = make_path_partition([6, 3, 3], [1, "a", 3])
    monkeypatch.setattr(
        multi_member_tree_proposals,
        "_candidate_district_pairs",
        lambda partition, pair_selection, rng: [(1, "a"), ("a", 3)],
    )
    calls: list[bool] = []

    def fake_bipartition_tree(
        subgraph: Graph | FrozenGraph,
        /,
        *,
        pop_col: str,
        pop_target: float,
        epsilon: float,
        node_repeats: int = 0,
        single_district_cut: bool = False,
        region_surcharge: dict[str, float] | None = None,
        allow_pair_reselection: bool = False,
        rng: random.Random,
    ) -> AbstractSet[Hashable]:
        calls.append(allow_pair_reselection)
        if len(calls) == 1:
            raise ReselectException("try another pair")
        nodes = set(list(subgraph.node_indices)[:3])
        return subgraph.translate_subgraph_node_ids_for_set_of_nodes(nodes)

    monkeypatch.setattr(multi_member_tree_proposals, "bipartition_tree", fake_bipartition_tree)
    proposal = proposals.MultiMemberReCom.district_pairs_mst(
        "population",
        3,
        0,
        {1: 2, "a": 1, 3: 1},
        allow_pair_reselection=True,
    )

    proposed = proposal(partition, rng=random.Random(0))

    assert calls == [True, True]
    assert proposed["population"] == {1: 6, "a": 3, 3: 3}
