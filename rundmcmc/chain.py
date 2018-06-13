
class MarkovChain:
    """
    MarkovChain is an iterator that allows the user to iterate over the states
    of a Markov chain run.

    Example usage:
    >>> chain = MarkovChain(proposal, is_valid, accept, initial_state)
    >>> for state in chain:
    >>>     # Do whatever you want - print output, compute metrics, ...

    :proposal: propose the next state from the current state
    :is_valid: is the proposed state within the space we're walking in?
    :accept: do we want to walk to the proposed state?
    :initial_state:
    :total_steps:
    """

    def __init__(self, proposal, is_valid, accept, initial_state, total_steps=1000):
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
