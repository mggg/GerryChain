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
Binary constraint functions
=================================================================================================
``no_worse_L1_reciprocal_polsby_popper``            Lower bounded L1-reciprocal Polsby-Popper
``no_worse_L_minus_1_reciprocal_polsby_popper``     Lower bounded L(-1)-reciprocal Polsby-Popper
``contiguous``                                      Districts are contiguous (with NetworkX methods)
``contiguous_bf``                                   Districts are contiguous (with a breadth-first search)
``single_flip_contiguous``                          Districts are contiguous (optimized for ``propose_random_flip`` proposal)
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

from .bounds import (LowerBound, SelfConfiguringLowerBound,
                     SelfConfiguringUpperBound, UpperBound,
                     WithinPercentRangeOfBounds)
from .compactness import (L1_polsby_popper, L1_reciprocal_polsby_popper,
                          L2_polsby_popper, L_minus_1_polsby_popper,
                          no_worse_L1_reciprocal_polsby_popper,
                          no_worse_L_minus_1_polsby_popper)
from .contiguity import (contiguous, contiguous_bfs, no_more_discontiguous,
                         single_flip_contiguous)
from .validity import (Validator, districts_within_tolerance,
                       no_vanishing_districts, refuse_new_splits,
                       within_percent_of_ideal_population)
