"""
Collection of constraint functions for the validation step in RunDMCMC.

=========================== ==============================================
Helper classes
==========================================================================
Validator                   Collection of constraints
Bounds                      Bounds on numeric constraints
UpperBounds                 Upper bounds on numeric constraints
LowerBounds                 Lower bounds on numeric constraints
SelfConfiguringUpperBound   Automatic upper bounds on numeric constraints
SelfConfiguringLowerBound   Automatic lower bounds on numeric constraints
WithinPercentRangeOfBounds  Percentage bounds for numeric constraints
==========================================================================

|

============================================== ==============================================
Boolean constraint functions
=============================================================================================
no_worse_L1_reciprocal_polsby_popper            Lower bounded L1-reciprocal Polsby-Popper
no_worse_L_minus_1_reciprocal_polsby_popper     Lower bounded L(-1)-reciprocal Polsby-Popper
single_flip_contiguous                          Contiguity of districts after single flips
contiguous                                      Contiguity of districts with NetworkX methods
no_more_disconnected                            No more disconnected districts than initially
no_vanishing_districts                          No districts may be completely consumed
============================================== ==============================================

Each new step proposed to the chain is passed off to the "validator" functions
here to determine whether or not the step is valid. If it is invalid (breaks
contiguity, for instance), then the step is immediately rejected.

The signature of a validator function should be as follows::

    def validator(partition):
        # check if valid
        # ...
        return is_valid

That is, validators take in a :class:`~rundmcmc.partition.Partition` instance,
and should return whether or not the instance is valid according to their
rules. Many top-level functions following this signature in this module are
examples of this.

"""

from .validity import (L1_reciprocal_polsby_popper,
                       L_minus_1_polsby_popper, Validator,
                       no_worse_L_minus_1_polsby_popper,
                       no_worse_L1_reciprocal_polsby_popper,
                       no_vanishing_districts, refuse_new_splits,
                       single_flip_contiguous, contiguous,
                       within_percent_of_ideal_population,
                       districts_within_tolerance,
                       fast_connected, no_more_disconnected,
                       non_bool_fast_connected, L1_polsby_popper,
                       L2_polsby_popper, proposed_changes_still_contiguous,
                       non_bool_where)

from .bounds import UpperBound, LowerBound, SelfConfiguringLowerBound, SelfConfiguringUpperBound
