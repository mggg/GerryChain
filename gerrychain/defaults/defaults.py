from gerrychain.accept import always_accept
from gerrychain.chain import MarkovChain
from gerrychain.constraints import (
    Validator,
    no_vanishing_districts,
    single_flip_contiguous,
)
from gerrychain.proposals import propose_random_flip

default_constraints = [single_flip_contiguous]


class DefaultChain(MarkovChain):
    """
    A MarkovChain with propose_random_flips proposal and always_accept
    acceptance function. Also instantiates a Validator for you from a
    list of constraints.
    """

    def __init__(self, partition, constraints, total_steps):
        if len(constraints) > 0:
            validator = Validator(constraints)
        else:
            validator = lambda x: True
        super().__init__(
            propose_random_flip, validator, always_accept, partition, total_steps
        )


grid_validator = Validator([single_flip_contiguous, no_vanishing_districts])


class GridChain(MarkovChain):
    """
    A basic MarkovChain for use with the Grid partition. The proposal is a single random flip
    at the boundary of a district. A step is valid if the districts are connected and no
    districts disappear. Requires a 'cut_edges' updater.
    """

    def __init__(self, initial_grid, total_steps=1000):
        if not initial_grid["cut_edges"]:
            raise ValueError(
                "BasicChain needs the Partition to have a cut_edges updater."
            )

        super().__init__(
            propose_random_flip,
            grid_validator,
            always_accept,
            initial_grid,
            total_steps=total_steps,
        )
