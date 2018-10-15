from unittest.mock import MagicMock

from gerrychain.chain import MarkovChain


class MockState:
    def merge(self, changes):
        return MockState()


def mock_proposal(state):
    return {1: 2}


def mock_accept(state):
    return True


def mock_is_valid(state):
    return True


def test_MarkovChain_runs_only_total_steps_times():
    for total_steps in range(1, 11):
        initial = MockState()
        chain = MarkovChain(mock_proposal, mock_is_valid, mock_accept, initial, total_steps)
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
    chain = MarkovChain(mock_proposal, mock_is_valid, mock_accept, initial, total_steps=10)

    counter = 0
    for state in chain:
        if counter == 0:
            assert state is initial
        else:
            assert state is not initial
        counter += 1
