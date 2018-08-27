from rundmcmc.accept import always_accept
from rundmcmc.chain import MarkovChain

from rundmcmc.proposals import propose_random_flip
from rundmcmc.validity import (L1_reciprocal_polsby_popper, UpperBound,
                               Validator, no_vanishing_districts,
                               single_flip_contiguous,
                               within_percent_of_ideal_population)

default_constraints = [single_flip_contiguous,
                       no_vanishing_districts]


class DefaultChain(MarkovChain):
    """
    A MarkovChain with propose_random_flips proposal and always_accept
    acceptance function. Also instantiates a Validator for you from a
    list of constraints.
    """

    def __init__(self, partition, constraints, total_steps):
        if no_vanishing_districts not in constraints:
            constraints.append(no_vanishing_districts)
        validator = Validator(constraints)
        super().__init__(self, propose_random_flip, validator,
                         always_accept, partition)


class BasicChain(MarkovChain):
    """
    The standard MarkovChain for replicating the Pennsylvania analysis. The proposal
    is a single random flip at the boundary of a district. A step is valid if the
    districts are connected, no districts disappear, and the populations of the districts
    are all within 1% of one another. Accepts every valid proposal.

    Requires a lot of different updaters.
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

        population_constraint = within_percent_of_ideal_population(initial_state, 0.01)

        compactness_limit = L1_reciprocal_polsby_popper(initial_state)
        compactness_constraint = UpperBound(L1_reciprocal_polsby_popper, compactness_limit)

        validator = Validator(default_constraints + [population_constraint, compactness_constraint])

        super().__init__(propose_random_flip, validator, always_accept, initial_state,
                         total_steps=total_steps)


grid_validator = Validator([single_flip_contiguous, no_vanishing_districts])


class GridChain(MarkovChain):
    """
    A very simple Markov chain. The proposal is a single random flip at the boundary of a district.
    A step is valid if the districts are connected and no districts disappear.
    Requires a 'cut_edges' updater.
    """

    def __init__(self, initial_grid, total_steps=1000):
        if not initial_grid['cut_edges']:
            raise ValueError('BasicChain needs the Partition to have a cut_edges updater.')

        super().__init__(propose_random_flip, grid_validator,
                         always_accept, initial_grid, total_steps=total_steps)
