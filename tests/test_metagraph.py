import pytest

from gerrychain import Partition, updaters
from gerrychain.metagraph import (all_cut_edge_flips, all_valid_flips,
                                  all_valid_states_one_flip_away)


@pytest.fixture
def partition(graph):
    assignment = dict(zip(range(9), [1, 1, 1, 1, 1, 1, 2, 2, 2]))
    return Partition(graph, assignment, {"cut_edges": updaters.cut_edges})


def test_all_cut_edge_flips(partition):
    
    # frm: TODO: Testing:  Maybe change all_cut_edge_flips to return a dict
    #
    # At present, it returns an iterator, which makes the code below
    # more complicated than it needs to be.  If it just returned
    # a dict, then the code would be:
    #
    #    result = set(
    #      node, part for all_cut_edge_flips(partition).items()
    #    )
    #
    result = set(
        (node, part)
        for flip in all_cut_edge_flips(partition)
        for node, part in flip.items()
    )

    # Convert from internal node_ids to "original" node_ids
    new_result = set()
    for internal_node_id, part in result:
        original_nx_node_id = partition.graph.original_nx_node_id_for_internal_node_id(internal_node_id)
        new_result.add((original_nx_node_id, part))

    assert new_result == {(6, 1), (7, 1), (8, 1), (4, 2), (5, 2), (3, 2)}


class TestAllValidStatesOneFlipAway:
    def test_accepts_callable_for_constraints(self, partition):
        constraints = lambda p: True
        result = all_valid_states_one_flip_away(partition, constraints)

        assert all(isinstance(state, Partition) for state in result)

    def test_accepts_list_of_constraints(self, partition):
        constraints = [lambda p: True]
        result = all_valid_states_one_flip_away(partition, constraints)

        assert all(isinstance(state, Partition) for state in result)


def test_all_valid_flips(partition):
    # frm: TODO: Testing:  NX vs. RX node_id issues...
    def disallow_six_to_one(partition):
        for node, part in partition.flips.items():
            if node == 6 and part == 1:
                return False
        return True

    constraints = [disallow_six_to_one]

    # frm: TODO: Testing:  If I created a utility routine to convert
    #             a list of flips to original node_ids,
    #             then I could use that here and then
    #             convert the resulting list to a set...

    result = set(
        (node, part)
        for flip in all_valid_flips(partition, constraints)
        for node, part in flip.items()
    )

    # Convert from internal node_ids to "original" node_ids
    new_result = set()
    for internal_node_id, part in result:
        original_nx_node_id = partition.graph.original_nx_node_id_for_internal_node_id(internal_node_id)
        new_result.add((original_nx_node_id, part))

    assert new_result == {(7, 1), (8, 1), (4, 2), (5, 2), (3, 2)}
