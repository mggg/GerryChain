import random

import pytest

from gerrychain import Partition, proposals, updaters


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
