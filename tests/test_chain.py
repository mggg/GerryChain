from rundmcmc.chain import MarkovChain


class MockState:
    def merge(self, changes):
        return MockState()


def mock_proposal(state):
    return state


def mock_accept(state):
    return True


def mock_is_valid(state):
    return True


def test_MarkovChain_runs_only_total_steps_times():
    initial = MockState()
    chain = MarkovChain(mock_proposal, mock_is_valid, mock_accept, initial, total_steps=10)
    counter = 0
    for state in chain:
        assert isinstance(state, MockState)
        if counter >= 10:
            assert False
        counter += 1
    if counter < 10:
        assert False
