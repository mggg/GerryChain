

class Loggers:
    def __init__(self, funcs=None, ends=None):
        """
            Loggers are essentially a wrapper object for a list of functions
            that run at certain intervals of the chain (with some added
            facilities).
            :funcs: List of functions of the format `name(state)`, where state
                    is an instance of the Partition class. Run on each
                    specified iteration of the chain.
            :ends:  List of functions of the format `name(state)`, where state
                    is an instance of the Partition class. Run after the chain
                    completes.
        """
        # Lists of functions.
        self.funcs = [] if funcs is None else funcs
        self.ends = [] if ends is None else ends

    def during_chain(self, state):
        """
            Runs all functions in `self.funcs`, each of which takes a `state`
            parameter, which is an instance of the Partition class. Run at
            each state in the chain.
            :state: Current state in the chain.
        """
        for func in self.funcs:
            func(state)

    def after_chain(self, state):
        """
            Runs all functions in `self.ends`, each of which takes a `state`
            parameter, which is an instance of the Partition class. Run after
            the chain completes.
            :state: Ending state of the chain.
        """
        for end in self.ends:
            end(state)
        