import inspect
import random
import warnings
from collections.abc import Callable, Hashable, Sequence
from typing import Any, cast

import networkx
import pytest

from gerrychain import MarkovChain, Partition
from gerrychain.accept import always_accept
from gerrychain.constraints import (
    Bounds,
    L1_polsby_popper,
    L1_reciprocal_polsby_popper,
    no_worse_L1_reciprocal_polsby_popper,
)
from gerrychain.graph import Graph
from gerrychain.partition.assignment import Assignment, level_sets
from gerrychain.tree import bipartition_tree
from gerrychain.tree.bipartition_tree import _Cut, _PopulatedGraph
from gerrychain.updaters import Election, Tally


class State:
    parent: "State | None" = None


def legacy_proposal(state: Partition) -> Partition:
    return cast(Partition, State())


def legacy_acceptance(state: Partition) -> bool:
    return True


def canonical_proposal(state: Partition, *, rng: random.Random) -> Partition:
    return cast(Partition, State())


def test_legacy_chain_keywords_and_callbacks_run() -> None:
    with pytest.warns(DeprecationWarning) as caught:
        chain = cast(Any, MarkovChain)(
            proposal=legacy_proposal,
            constraints=lambda state: True,
            accept=legacy_acceptance,
            initial_state=cast(Partition, State()),
            total_steps=2,
        )
        assert len(list(chain)) == 2

    messages = [str(warning.message) for warning in caught]
    for old_name, new_name in (
        ("proposal", "proposal_fn"),
        ("accept", "acceptance_fn"),
        ("initial_state", "initial_partition"),
    ):
        assert any(old_name in message and new_name in message for message in messages)
    assert sum("pre-1.0 callback signature" in message for message in messages) == 2


def test_canonical_chain_does_not_warn() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        chain = MarkovChain(
            proposal_fn=canonical_proposal,
            constraints=lambda state: True,
            acceptance_fn=always_accept,
            initial_partition=cast(Partition, State()),
            total_steps=2,
        )
        assert len(list(chain)) == 2

    assert caught == []


def test_legacy_and_canonical_keyword_conflict() -> None:
    with pytest.raises(TypeError, match="both 'proposal' and 'proposal_fn'"):
        cast(Any, MarkovChain)(
            proposal=legacy_proposal,
            proposal_fn=canonical_proposal,
            total_steps=1,
        )


def test_legacy_keywords_stay_out_of_canonical_signatures() -> None:
    assert "proposal" not in inspect.signature(MarkovChain).parameters
    assert "flips" not in inspect.signature(Partition.from_random_assignment).parameters
    assert "dtype" not in inspect.signature(Tally).parameters


def test_ignored_random_assignment_flips_warns(three_by_three_grid: Graph) -> None:
    for node in three_by_three_grid.node_indices:
        three_by_three_grid.node_data(node)["population"] = 1

    def partition_fn(
        *,
        graph: Graph,
        parts: Sequence[Hashable],
        pop_target: float,
        pop_col: str,
        epsilon: float,
        rng: random.Random,
    ) -> dict[Hashable, Hashable]:
        return {node: 0 for node in graph.node_indices}

    with pytest.warns(DeprecationWarning, match="flips.*deprecated and ignored"):
        partition = cast(Any, Partition.from_random_assignment)(
            three_by_three_grid,
            n_parts=1,
            epsilon=0.01,
            pop_col="population",
            partition_fn=partition_fn,
            flips={0: 1},
        )

    assert len(partition.parts) == 1


@pytest.mark.parametrize(
    ("call", "old_name", "new_name"),
    [
        (lambda: cast(Any, Bounds)(func=lambda: [1], bounds=(0, 2)), "func", "value_fn"),
        (
            lambda: cast(Any, Assignment.from_dict)(assignment={0: 1}),
            "assignment",
            "nodes_to_parts",
        ),
        (lambda: cast(Any, level_sets)({0: 1}, container=set), "container", "container_fn"),
        (lambda: cast(Any, Tally)("population", dtype=float), "dtype", "dtype_fn"),
        (
            lambda: cast(Any, Election)("election", parties_to_columns={"A": "votes"}),
            "parties_to_columns",
            "party_names_to_node_attribute_names",
        ),
    ],
)
def test_representative_renamed_keywords_warn(
    call: Callable[[], object],
    old_name: str,
    new_name: str,
) -> None:
    with pytest.warns(DeprecationWarning) as caught:
        call()
    message = str(caught[0].message)
    assert old_name in message
    assert new_name in message


def test_l1_names_are_canonical() -> None:
    from gerrychain import constraints

    assert constraints.L1_polsby_popper is L1_polsby_popper
    assert constraints.L1_reciprocal_polsby_popper is L1_reciprocal_polsby_popper
    assert constraints.no_worse_L1_reciprocal_polsby_popper is no_worse_L1_reciprocal_polsby_popper
    assert not hasattr(constraints, "L_1_polsby_popper")


def test_legacy_callback_type_error_is_not_retried() -> None:
    calls = 0

    def broken_proposal(state: Partition) -> Partition:
        nonlocal calls
        calls += 1
        raise TypeError("inside proposal")

    with pytest.warns(DeprecationWarning, match="pre-1.0 callback signature"):
        chain = MarkovChain(
            proposal_fn=cast(Any, broken_proposal),
            initial_partition=cast(Partition, State()),
            total_steps=2,
        )
        iterator = iter(chain)

    next(iterator)
    with pytest.raises(TypeError, match="inside proposal"):
        next(iterator)
    assert calls == 1


def test_legacy_tree_keywords_and_callbacks_run() -> None:
    nx_graph = networkx.path_graph(4)
    networkx.set_node_attributes(nx_graph, {node: 1 for node in nx_graph}, "population")
    graph = Graph.from_networkx(nx_graph)

    def spanning_tree_fn(graph: Graph) -> Graph:
        return graph

    def find_cuts(
        populated_graph: _PopulatedGraph,
        one_sided_cut: bool = False,
        choice: Callable[[Sequence[Hashable]], Hashable] = random.choice,
    ) -> list[_Cut]:
        return [_Cut((1, 2), 1, frozenset({0, 1}))]

    def cut_choice(cuts: list[_Cut]) -> _Cut:
        return cuts[0]

    with pytest.warns(DeprecationWarning) as caught:
        nodes = cast(Any, bipartition_tree)(
            graph=graph,
            pop_col="population",
            pop_target=2,
            epsilon=0.01,
            spanning_tree_fn=spanning_tree_fn,
            balance_edge_fn=find_cuts,
            one_sided_cut=False,
            cut_choice=cut_choice,
        )

    assert nodes == frozenset({0, 1})
    messages = [str(warning.message) for warning in caught]
    assert any(
        "balance_edge_fn" in message and "find_balanced_edge_cuts_fn" in message
        for message in messages
    )
    assert any("pre-1.0 callback signature" in message for message in messages)
