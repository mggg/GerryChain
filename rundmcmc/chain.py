
class MarkovChain:
    """
    MarkovChain is an iterator that allows the user to iterate over the states
    of a Markov chain run.

    Example usage:

    .. highlight:: python

        chain = MarkovChain(proposal, is_valid, accept, initial_state)
        for state in chain:
            # Do whatever you want - print output, compute metrics, ...

    """

    def __init__(self, proposal, is_valid, accept, initial_state, total_steps=1000):
        """
        :proposal: Function proposing the next state from the current state.
        :is_valid: :class:`Validator` class instance.
        :accept: Function accepting or rejecting the proposed state.
        :initial_state: Initial :class:`Partition` class.
        :total_steps: Number of steps to run.
        """
        self.proposal = proposal
        self.is_valid = is_valid
        self.accept = accept
        self.total_steps = total_steps
        self.state = initial_state

    def __iter__(self):
        self.counter = 0
        return self

    def __next__(self):
        while self.counter < self.total_steps:
            proposal = self.proposal(self.state)
            proposed_next_state = self.state.merge(proposal)
            if self.is_valid(proposed_next_state):
                if self.accept(proposed_next_state):
                    self.state = proposed_next_state
                self.counter += 1
                return proposed_next_state
        raise StopIteration
