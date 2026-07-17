import random
from collections.abc import Callable
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from gerrychain.chain import MarkovChain
from gerrychain.partition import Partition


class MockState:
    def flip(
        self, changes: dict[int, int], flips_passed_in_use_original_nx_node_ids: bool
    ) -> "MockState":
        return MockState()


def mock_state() -> Partition:
    # MockState stands in for Partition; the chain only ever calls flip() on the state.
    return cast(Partition, MockState())


def mock_proposal(state: Partition, *, rng: random.Random) -> Partition:
    return cast(
        Partition,
        cast(MockState, state).flip({1: 2}, flips_passed_in_use_original_nx_node_ids=True),
    )


def mock_accept(state: Partition, *, rng: random.Random) -> bool:
    return True


def mock_is_valid(state: Partition) -> bool:
    return True


def test_MarkovChain_runs_only_total_steps_times():
    for total_steps in range(1, 11):
        initial = mock_state()
        chain = MarkovChain(mock_proposal, mock_is_valid, mock_accept, initial, total_steps)
        counter = 0
        for state in chain:
            assert isinstance(state, MockState)
            if counter >= total_steps:
                assert False
            counter += 1
        if counter < total_steps:
            assert False


def test_MarkovChain_returns_the_initial_partition_first():
    initial = MagicMock()
    chain = MarkovChain(mock_proposal, mock_is_valid, mock_accept, initial, total_steps=10)

    counter = 0
    for state in chain:
        if counter == 0:
            assert state is initial
        else:
            assert state is not initial
        counter += 1


def test_chain_only_yields_accepted_states():
    class Value:
        def __init__(self, value: int):
            self.value = value

    values = list(reversed([Value(x) for x in [0, 1, 2, 3, -1, -2, -3, -4]]))

    def accept(value: Partition, *, rng: random.Random) -> bool:
        return cast(Value, value).value <= 0

    def proposal(value: Partition, *, rng: random.Random) -> Partition:
        return cast(Partition, values.pop())

    chain = MarkovChain(
        proposal_fn=proposal,
        constraints=lambda x: True,
        acceptance_fn=accept,
        initial_partition=cast(Partition, Value(0)),
        total_steps=4,
    )

    for state in chain:
        assert cast(Value, state).value <= 0, "The chain yielded a non-accepted state"


def test_incremental_construction_matches_constructor():
    initial = mock_state()
    chain = MarkovChain(total_steps=5)
    chain.initial_partition = initial
    chain.proposal_fn = mock_proposal
    chain.constraints = mock_is_valid
    chain.acceptance_fn = mock_accept

    assert len(list(chain)) == 5


def test_check_valid_names_missing_config():
    chain = MarkovChain(total_steps=5)
    with pytest.raises(ValueError, match="proposal_fn, initial_partition"):
        chain.check_valid()

    with pytest.raises(ValueError, match="not fully configured"):
        next(iter(chain))


def test_iter_rejects_invalid_initial_partition():
    def never_valid(state: Partition) -> bool:
        return False

    chain = MarkovChain(proposal_fn=mock_proposal, acceptance_fn=mock_accept, total_steps=5)
    chain.constraints = never_valid  # no initial_partition yet, so this cannot validate
    chain.initial_partition = mock_state()
    with pytest.raises(ValueError, match="never_valid"):
        next(iter(chain))


def test_add_constraint_defers_check_until_iteration():
    def never_valid(state: Partition) -> bool:
        return False

    chain = MarkovChain(proposal_fn=mock_proposal, acceptance_fn=mock_accept, total_steps=3)
    chain.add_constraint(never_valid)  # no initial_partition yet: recorded, not checked
    chain.initial_partition = mock_state()
    with pytest.raises(ValueError, match="never_valid"):
        next(iter(chain))


def test_add_constraint_validates_immediately_with_initial_partition():
    def never_valid(state: Partition) -> bool:
        return False

    chain = MarkovChain(
        proposal_fn=mock_proposal,
        acceptance_fn=mock_accept,
        initial_partition=mock_state(),
        total_steps=3,
    )
    with pytest.raises(ValueError, match="never_valid"):
        chain.add_constraint(never_valid)
    # The failing constraint was not retained.
    assert never_valid not in chain.constraints.constraints


def test_add_updater_applies_before_or_after_initial_partition():
    class StateWithUpdaters(MockState):
        def __init__(self) -> None:
            self.updaters: dict[str, Callable[[Partition], Any]] = {}

    def answer(partition: Partition) -> int:
        return 42

    def zero(partition: Partition) -> int:
        return 0

    chain = MarkovChain(proposal_fn=mock_proposal, acceptance_fn=mock_accept, total_steps=3)
    chain.add_updater("answer", answer)  # before any initial_partition: applied on assignment
    initial = StateWithUpdaters()
    chain.initial_partition = cast(Partition, initial)
    assert initial.updaters["answer"] is answer

    chain.add_updater("zero", zero)  # after: applied immediately
    assert initial.updaters["zero"] is zero


def test_add_constraint_and_add_updater_rejected_while_locked():
    chain = MarkovChain(mock_proposal, mock_is_valid, mock_accept, mock_state(), total_steps=3)
    it = iter(chain)
    next(it)
    with pytest.raises(AttributeError, match="locked"):
        chain.add_constraint(mock_is_valid)
    with pytest.raises(AttributeError, match="locked"):
        chain.add_updater("x", lambda partition: None)


def test_constraints_setter_still_validates_eagerly():
    chain = MarkovChain(
        proposal_fn=mock_proposal,
        acceptance_fn=mock_accept,
        initial_partition=mock_state(),
        total_steps=5,
    )
    with pytest.raises(ValueError, match="lambda"):
        chain.constraints = lambda state: False


def test_config_locked_while_running_and_unlocked_after():
    chain = MarkovChain(mock_proposal, mock_is_valid, mock_accept, mock_state(), total_steps=3)
    it = iter(chain)
    next(it)
    with pytest.raises(AttributeError, match="locked"):
        chain.total_steps = 100
    next(it)
    next(it)
    with pytest.raises(StopIteration):
        next(it)
    # Exhausting the run unlocks the configuration again.
    chain.total_steps = 5
    assert len(list(chain)) == 5


def test_chain_abandoned_by_break_unlocks_and_can_be_rerun():
    chain = MarkovChain(mock_proposal, mock_is_valid, mock_accept, mock_state(), total_steps=3)
    for _ in chain:
        break

    # Leaving the loop ends the run and releases the lock.
    chain.acceptance_fn = mock_accept

    count = 0
    for _ in chain:
        count += 1

    assert count == 3


def test_chain_unlocks_when_a_step_raises():
    def exploding_proposal(state: Partition, *, rng: random.Random) -> Partition:
        raise RuntimeError("boom")

    chain = MarkovChain(exploding_proposal, mock_is_valid, mock_accept, mock_state(), total_steps=3)
    it = iter(chain)
    next(it)  # the initial state is yielded without calling the proposal
    with pytest.raises(RuntimeError, match="boom"):
        next(it)
    # The failure unlocked the chain, so it can be reconfigured.
    chain.proposal_fn = mock_proposal
    assert len(list(chain)) == 3


def test_repr():
    chain = MarkovChain(
        proposal_fn=lambda x, *, rng: x,
        constraints=[],
        acceptance_fn=lambda x, *, rng: True,
        initial_partition=None,
        total_steps=100,
    )

    assert repr(chain) == "<MarkovChain [100 steps]>"
