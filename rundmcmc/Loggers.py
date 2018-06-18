
class DataFrameLogger:
    """DataFrameLogger builds a pandas DataFrame with data from each state of
    the random walk.
    :keys: list of the names of the properties that you want to record for each state
    """
    pass


class ListLogger:
    def __init__(self, key):
        self.key = key

    def before(self, state):
        self.data = []

    def during(self, state):
        self.data.append(state[self.key])

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
