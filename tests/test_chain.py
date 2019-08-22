from unittest.mock import MagicMock

from gerrychain.chain import MarkovChain


class MockState:
    def flip(self, changes):
        return MockState()


def mock_proposal(state):
    return state.flip({1: 2})


def mock_accept(state):
    return True


def mock_is_valid(state):
    return True


def test_MarkovChain_runs_only_total_steps_times():
    for total_steps in range(1, 11):
        initial = MockState()
        chain = MarkovChain(
            mock_proposal, mock_is_valid, mock_accept, initial, total_steps
        )
        counter = 0
        for state in chain:
            assert isinstance(state, MockState)
            if counter >= total_steps:
                assert False
            counter += 1
        if counter < total_steps:
            assert False


def test_MarkovChain_returns_the_initial_state_first():
    initial = MagicMock()
    chain = MarkovChain(
        mock_proposal, mock_is_valid, mock_accept, initial, total_steps=10
    )

    counter = 0
    for state in chain:
        if counter == 0:
            assert state is initial
        else:
            assert state is not initial
        counter += 1


def test_chain_only_yields_accepted_states():
    class Value:
        def __init__(self, value):
            self.value = value

    values = list(reversed([Value(x) for x in [0, 1, 2, 3, -1, -2, -3, -4]]))

    def accept(value):
        return value.value <= 0

    def proposal(value):
        return values.pop()

    chain = MarkovChain(
        proposal=proposal,
        constraints=lambda x: True,
        accept=accept,
        initial_state=Value(0),
        total_steps=4,
    )

    for state in chain:
        assert accept(state), "The chain yielded a non-accepted state"


def test_repr():
    chain = MarkovChain(
        proposal=lambda x: None,
        constraints=[],
        accept=lambda x: True,
        initial_state=None,
        total_steps=100,
    )

    assert repr(chain) == "<MarkovChain [100 steps]>"
