from rundmcmc.run import run


class MockChain:
    def __init__(self, states):
        self.states = iter(states)
        self.state = states[0]

    def __iter__(self):
        return self

    def __next__(self):
        self.state = next(self.states)
        return self.state


class MockLogger:
    def __init__(self):
        self.calls = {'before': 0, 'after': 0, 'during': 0}

    def before(self, state):
        self.calls['before'] += 1

    def during(self, state):
        self.calls['during'] += 1

    def after(self, state):
        self.calls['after'] += 1


def test_run():
    logger1, logger2 = MockLogger(), MockLogger()
    chain = MockChain([0, 1, 2, 3, 4])
    run(chain, [logger1, logger2])
    for logger in [logger1, logger2]:
        assert logger.calls['before'] == 1
        assert logger.calls['during'] == 5
        assert logger.calls['after'] == 1
