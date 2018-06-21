import math

import pandas as pd


class FlatListLogger:
    """
    FlatListLogger collects the value of the property specified by key for
    all of the parts of the partition at every state in the chain, and returns
    this as a list in its `after` method.

    This logger is only here until we come up with a better way to handle the
    data we want to collect. I should not have even written this docstring.
    """

    def __init__(self, key):
        self.key = key

    def before(self, chain):
        self.data = []

    def during(self, state):
        self.data += state[self.key].values()

    def after(self, state):
        return self.data


class ConsoleLogger:
    """
    ConsoleLogger just prints the state to the console at each step of the
    chain, at the prescribed interval.
    """

    def __init__(self, interval=0):
        self.interval = interval

    def before(self, chain):
        print(chain.state)
        self.counter = 0

    def during(self, state):
        if self.counter % self.interval == 0:
            print(state)

    def after(self, state):
        print("Chain run complete!")
        return True


class DataFrameLogger:
    """
    DataFrameLogger samples the states of the chain to load up a reasonably-
    sized DataFrame of the specified computed scores.
    """

    def __init__(self, scores, sample_rate=1):
        self.sample_rate = sample_rate
        self.scores = scores

    def before(self, chain):
        if not self.sample_rate:
            self.sample_rate = math.floor(len(chain) * 0.01)
        self.counter = 0

        initial_data = self.compute_scores(chain.state)
        self.data = pd.DataFrame(initial_data)

    def during(self, state):
        self.data.append(self.compute_scores(state))

    def after(self, state):
        return self.data

    def compute_scores(self, state):
        return {key: score(state) for key, score in self.scores.items()}
