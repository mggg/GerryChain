import pandas as pd


class DataFrameLogger:
    """DataFrameLogger builds a pandas DataFrame with data from each state of
    the random walk.
    :keys: list of the names of the properties that you want to record for each state
    """

    def __init__(self, keys=None):
        self.keys = keys

    def before(self, state):
        self.data = pd.DataFrame(columns=self.keys)

    def during(self, state):
        new_row = pd.DataFrame.from_dict(state.fields)
        print(new_row)
        self.data.append(new_row)

    def after(self, state):
        return self.data


class ConsoleLogger:
    """ConsoleLogger just prints the state to the console at each step of the
    chain, at the prescribed interval.
    """

    def __init__(self, interval=0):
        self.interval = interval

    def before(self, state):
        print(state)
        self.counter = 0

    def during(self, state):
        if self.counter % self.interval == 0:
            print(state)

    def after(self, state):
        print("Chain run complete!")
