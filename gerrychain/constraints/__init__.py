"""
The `gerrychain.constraints` module provides a collection of constraint
functions and helper classes for the validation step in GerryChain.

Helper classes include ``Validator`` for collections of constraints, numeric ``Bounds`` and
``UpperBound``/``LowerBound`` classes, self-configuring bounds, and percentage bounds.

Binary constraint functions include contiguity checks, ``no_vanishing_districts``, and lower
bounds on reciprocal Polsby-Popper scores.

Each new step proposed to the chain is passed off to the "validator" functions
here to determine whether or not the step is valid. If it is invalid (breaks
contiguity, for instance), then the step is immediately rejected.

A validator should take in a Partition instance,
and should return whether or not the instance is valid according to their
rules. Many top-level functions following this signature in this module are
examples of this.
"""

from .bounds import (
    Bounds,
    LowerBound,
    SelfConfiguringLowerBound,
    SelfConfiguringUpperBound,
    UpperBound,
    WithinPercentRangeOfBounds,
)
from .compactness import (
    L2_polsby_popper,
    L_1_polsby_popper,
    L_1_reciprocal_polsby_popper,
    L_minus_1_polsby_popper,
    no_worse_L_1_reciprocal_polsby_popper,
    no_worse_L_minus_1_polsby_popper,
)
from .contiguity import (
    contiguous,
    no_more_discontiguous,
    single_flip_contiguous,
)
from .validity import (
    Validator,
    deviation_from_ideal,
    districts_within_tolerance,
    no_vanishing_districts,
    refuse_new_splits,
    within_percent_of_ideal_population,
)

__all__ = [
    "LowerBound",
    "SelfConfiguringLowerBound",
    "SelfConfiguringUpperBound",
    "UpperBound",
    "WithinPercentRangeOfBounds",
    "L_1_polsby_popper",
    "L_1_reciprocal_polsby_popper",
    "L2_polsby_popper",
    "L_minus_1_polsby_popper",
    "no_worse_L_1_reciprocal_polsby_popper",
    "no_worse_L_minus_1_polsby_popper",
    "contiguous",
    "no_more_discontiguous",
    "single_flip_contiguous",
    "Validator",
    "deviation_from_ideal",
    "districts_within_tolerance",
    "no_vanishing_districts",
    "refuse_new_splits",
    "within_percent_of_ideal_population",
    "Bounds",
]
