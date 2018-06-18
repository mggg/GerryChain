
class FlatListLogger:
    """FlatListLogger collects the value of the property specified by key for
    all of the parts of the partition at every state in the chain, and returns
    this as a list in its `after` method.

    This logger is only here until we come up with a better way to handle the
    data we want to collect. I should not have even written this docstring.
    """

    def __init__(self, key):
        self.key = key

    def before(self, state):
        self.data = []

    def during(self, state):
        self.data += state[self.key].values()

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
        return True
