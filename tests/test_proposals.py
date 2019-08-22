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
        proposals.propose_chunk_flip,
        proposals.propose_flip_every_district,
        proposals.propose_random_flip,
        proposals.slow_reversible_propose,
        proposals.slow_reversible_propose_bi,
        proposals.spectral_recom,
    ],
)
def test_proposal_returns_a_partition(proposal, partition):
    proposed = proposal(partition)
    assert isinstance(proposed, partition.__class__)
