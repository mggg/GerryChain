from rundmcmc.accept import always_accept
from rundmcmc.chain import MarkovChain
from rundmcmc.proposals import propose_random_flip
from rundmcmc.validity import (Validator, contiguous,
                               districts_within_tolerance,
                               no_vanishing_districts)

default_validator = Validator([contiguous, no_vanishing_districts, districts_within_tolerance])


class BasicChain(MarkovChain):
    """
    A basic MarkovChain. The proposal is a single random flip at the boundary of a district.
    A step is valid if the districts are contiguous, no districts disappear, and the
    populations of the districts are all within 1% of one another.
    Accepts every valid proposal.

    Requires 'cut_edges' and 'population' updaters.
    """

    def __init__(self, initial_state, total_steps=1000):
        """
        :initial_state: the initial graph partition. Must have a cut_edges updater
        :total_steps: (defaults to 1000) the total number of steps that the random walk
        should perform.
        """
        if not initial_state['cut_edges']:
            raise ValueError('BasicChain needs the Partition to have a cut_edges updater.')
        if not initial_state['population']:
            raise ValueError('BasicChain needs the Partition to have a population updater.')
        super().__init__(self, propose_random_flip, default_validator,
                         always_accept, initial_state, total_steps)
