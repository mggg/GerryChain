from rundmcmc.accept import always_accept
from rundmcmc.chain import MarkovChain
from rundmcmc.proposals import propose_random_flip
from rundmcmc.validity import Validator, contiguous, no_vanishing_districts

default_validator = Validator([contiguous, no_vanishing_districts])


class BasicChain(MarkovChain):
    """
    A basic MarkovChain. The proposal is a single random flip at the boundary of a district.
    A step is valid if the districts are contiguous and no districts disappear.
    Accepts every valid proposal.
    """

    def __init__(self, initial_state, total_steps=1000):
        """
        :initial_state: the initial graph partition. Must have a cut_edges updater
        :total_steps: (defaults to 1000) the total number of steps that the random walk
        should perfor.
        """
        if not initial_state['cut_edges']:
            raise ValueError('BasicChain needs the Partition to have a cut_edges updater.')
        super().__init__(self, propose_random_flip, default_validator,
                         always_accept, initial_state, total_steps)
