import random
from functools import partial

import pytest

from gerrychain import Partition, proposals, updaters
from gerrychain.tree import bipartition_tree, uniform_spanning_tree


@pytest.fixture
def partition(graph):
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
def test_proposal_returns_a_partition(proposal, partition):
    proposed = proposal(partition, rng=random.Random(0))
    assert isinstance(proposed, partition.__class__)


def test_proposals_support_mixed_type_part_labels(graph):
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
def populated_partition(graph):
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
def test_recom_variants_return_balanced_partitions(build_proposal, populated_partition):
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
def test_recom_variants_run_with_pair_reselection(build_proposal, populated_partition):
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
def test_recom_variants_match_direct_recom_calls(build_proposal, recom_kwargs, populated_partition):
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


def test_reversible_variant_matches_direct_reversible_recom_call(populated_partition):
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


def test_recom_reversible_variant_runs(populated_partition):
    proposal = proposals.ReCom.reversible(
        pop_col="population", pop_target=3, epsilon=0, max_balanced_edge_cuts=100
    )
    proposed = proposal(populated_partition, rng=random.Random(0))
    assert isinstance(proposed, Partition)


def test_recom_rejects_unknown_pair_selection(populated_partition):
    with pytest.raises(ValueError, match="pair_selection"):
        proposals.recom(
            populated_partition,
            pop_col="population",
            pop_target=3,
            epsilon=0,
            pair_selection="nope",
            rng=0,
        )


def test_cut_edges_pair_selection_weights_by_shared_boundary(graph):
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

    def count_bc_first(pair_selection):
        count = 0
        for seed in range(600):
            pairs = list(_candidate_district_pairs(partition, pair_selection, random.Random(seed)))
            assert sorted(pairs) == [("a", "b"), ("a", "c"), ("b", "c")]
            count += pairs[0] == ("b", "c")
        return count

    # Expected 300 of 600 for cut_edges, 200 of 600 for district_pairs.
    assert count_bc_first("cut_edges") > 260
    assert count_bc_first("district_pairs") < 240
