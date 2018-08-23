class MarkovChain:
    """
    MarkovChain is an iterator that allows the user to iterate over the states
    of a Markov chain run.

    Example usage:

    .. code-block:: python

        chain = MarkovChain(proposal, is_valid, accept, initial_state)
        for state in chain:
            # Do whatever you want - print output, compute scores, ...

    """

    def __init__(self, proposal, is_valid, accept, initial_state, total_steps=1000):
        """
        :proposal: Function proposing the next state from the current state.
        :is_valid: :class:`~rundmcmc.validity.Validator` class instance.
        :accept: Function accepting or rejecting the proposed state.
        :initial_state: Initial :class:`rundmcmc.partition.Partition` class.
        :total_steps: Number of steps to run.

        """
        if not is_valid(initial_state):
            failed = [
                constraint for constraint in is_valid.constraints if not constraint(initial_state)]
            message = 'The given initial_state is not valid according is_valid. ' \
                      'The failed constraints were: ' + ','.join([f.__name__ for f in failed])
            raise ValueError(message)

        self.proposal = proposal
        self.is_valid = is_valid
        self.accept = accept
        self.total_steps = total_steps
        self.state = initial_state

    def __iter__(self):
        self.counter = 0
        return self

    def __next__(self):
        if self.counter == 0:
            self.counter += 1
            return self.state

        while self.counter < self.total_steps:
            proposal = self.proposal(self.state)

            if not proposal:
                if self.accept(self.state):
                    self.counter += 1
                    return self.state
                else:
                    continue

            proposed_next_state = self.state.merge(proposal)
            # Erase the parent of the parent, to avoid memory leak
            self.state.parent = None

            if self.is_valid(proposed_next_state):
                proposed_next_state.accepted = self.accept(proposed_next_state)
                if proposed_next_state.accepted:
                    self.state = proposed_next_state
                self.counter += 1
                # Yield the proposed state, even if not accepted
                return proposed_next_state
        raise StopIteration

    def __len__(self):
        return self.total_steps
