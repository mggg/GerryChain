"""
The :mod:`gerrychain.constraints` module provides a collection of constraint
functions and helper classes for the validation step in GerryChain.

=============================== ===============================================
Helper classes
===============================================================================
``Validator``                    Collection of constraints
``Bounds``                       Bounds on numeric constraints
``UpperBounds``                  Upper bounds on numeric constraints
``LowerBounds``                  Lower bounds on numeric constraints
``SelfConfiguringUpperBound``    Automatic upper bounds on numeric constraints
``SelfConfiguringLowerBound``    Automatic lower bounds on numeric constraints
``WithinPercentRangeOfBounds``   Percentage bounds for numeric constraints
===============================================================================

|

================================================== ==============================================
Boolean constraint functions
=================================================================================================
``no_worse_L1_reciprocal_polsby_popper``            Lower bounded L1-reciprocal Polsby-Popper
``no_worse_L_minus_1_reciprocal_polsby_popper``     Lower bounded L(-1)-reciprocal Polsby-Popper
``single_flip_contiguous``                          Contiguity of districts after single flips
``contiguous``                                      Contiguity of districts with NetworkX methods
``no_more_disconnected``                            No more disconnected districts than initially
``no_vanishing_districts``                          No districts may be completely consumed
================================================== ==============================================

Each new step proposed to the chain is passed off to the "validator" functions
here to determine whether or not the step is valid. If it is invalid (breaks
contiguity, for instance), then the step is immediately rejected.

A validator should take in a :class:`~gerrychain.partition.Partition` instance,
and should return whether or not the instance is valid according to their
rules. Many top-level functions following this signature in this module are
examples of this.

"""

from .bounds import (
    LowerBound,
    SelfConfiguringLowerBound,
    SelfConfiguringUpperBound,
    UpperBound,
)
from .validity import (
    L1_polsby_popper,
    L1_reciprocal_polsby_popper,
    L2_polsby_popper,
    L_minus_1_polsby_popper,
    Validator,
    contiguous,
    districts_within_tolerance,
    fast_connected,
    no_more_disconnected,
    no_vanishing_districts,
    no_worse_L1_reciprocal_polsby_popper,
    no_worse_L_minus_1_polsby_popper,
    non_bool_fast_connected,
    non_bool_where,
    proposed_changes_still_contiguous,
    refuse_new_splits,
    single_flip_contiguous,
    within_percent_of_ideal_population,
)
