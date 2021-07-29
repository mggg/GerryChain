from ..chain import MarkovChain
from ..accept import always_accept
from ..random import random

import numpy as np


class SingleMetricOptimizer:
    """
    SingleMetricOptimizer represents the class of algorithms / chains that optimize plans with
    respect to a single metric.  This class implements some common methods of optimization.
    """

    def __init__(self, proposal, constraints, initial_state, optimization_metric, minmax="max",
                 tracking_funct=None):
        """
        :param `proposal`: Function proposing the next state from the current state.
        :param `constraints`: A function with signature ``Partition -> bool`` determining whether
            the proposed next state is valid (passes all binary constraints). Usually this is a
            :class:`~gerrychain.constraints.Validator` class instance.
        :param `initial_state`: Initial :class:`gerrychain.partition.Partition` class.
        :param `optimization_metric`: The score function with which to optimize over.  This should
            have the signiture: ``Partition -> 'a where 'a is Comparable``
        :param `minmax`: Whether to minimize or maximize the function?
        :param `tracking_funct`: A function with the signiture ``Partition -> None`` to be run at
            every step of the chain.  If you'd like to externaly track stats beyond those reflected
            in the optimation_metric here is where to implement that.
        """
        self.part = initial_state
        self.proposal = proposal
        self.constraints = constraints
        self.score = optimization_metric
        self.maximize = minmax == "max" or minmax == "maximize"
        self.tracking_funct = tracking_funct if tracking_funct is not None else lambda p: None

    def _is_improvement(self, part_score, max_score):
        if self.maximize:
            return part_score >= max_score
        else:
            return part_score <= max_score

    def short_bursts(self, burst_length, num_bursts, accept=always_accept):
        """
        Preforms a short burst run using the instance's score function.  Each burst starts at the
        best preforming plan of the previsdous burst.  If there's a tie, the later observed one is
        selected.

        :param `burst_length` (int): How many steps to run within each burst?
        :param `num_bursts` (int): How many bursts to preform?
        :param `accept`: Function accepting or rejecting the proposed state. In the most basic
            use case, this always returns ``True``.

        :rtype (Partition * np.array): Tuple of maximal (or minimal) observed partition and a 2D
            numpy array of observed scores over each of the bursts.
        """
        max_part = (self.part, self.score(self.part))
        observed_scores = np.zeros((num_bursts, burst_length))

        for i in range(num_bursts):
            chain = MarkovChain(self.proposal, self.constraints, accept, max_part[0], burst_length)

            for j, part in enumerate(chain):
                part_score = self.score(part)
                observed_scores[i][j] = part_score

                if self._is_improvement(part_score, max_part[1]):
                    max_part = (part, part_score)

                self.tracking_fun(part)

        return (max_part[0], observed_scores)

    def _titled_acceptance_function(self, p):
        """
        Function factory that binds and returns a tilted acceptance function.

        :rtype (``Partition -> Bool``)
        """
        def tilted_acceptance_function(part):
            if part.parent is None:
                return True

            part_score = self.score(part)
            prev_score = self.score(part.parent)

            if self.maximize and part_score >= prev_score:
                return True
            elif not self.maximize and part_score <= prev_score:
                return True
            else:
                return random.random() < p

        return tilted_acceptance_function

    def tilted_short_bursts(self, burst_length, num_bursts, p):
        """
        Preforms a short burst run using the instance's score function.  Each burst starts at the
        best preforming plan of the previsdous burst.  If there's a tie, the later observed one is
        selected.  Within each burst a tilted acceptance function is used where better scoring plans
        are always accepted and worse scoring plans are accepted with probability `p`.

        :param `burst_length` (int): How many steps to run within each burst?
        :param `num_bursts` (int): How many bursts to preform?
        :param `p` (float): The probability with which to accept worse scoring plans.

        :rtype (Partition * np.array): Tuple of maximal (or minimal) observed partition and a 2D
            numpy array of observed scores over each of the bursts.
        """
        return self.short_bursts(burst_length, num_bursts,
                                 accept=self._titled_acceptance_function(p))

    def variable_lenght_short_bursts(self, num_steps, stuck_buffer, accept=always_accept):
        """
        Preforms a short burst where the burst length is alowed to increase as it gets harder to
        find high scoring plans.  The initial burst length is set to 2, and it is doubled each time
        there is no improvement over the passed number (`stuck_buffer`) of runs.

        :param `num_steps` (int): Total number of steps to take overall.
        :param `stuck_buffer` (int): How many bursts of a given length with no improvement to allow
            before imcreasing the burst length.
        :param accept: Function accepting or rejecting the proposed state. In the most basic
            use case, this always returns ``True``.

        :rtype (Partition * np.array): Tuple of maximal (or minimal) observed partition and a 1D
            numpy array of observed scores over each of the bursts.
        """
        max_part = (self.part, self.score(self.part))
        observed_scores = np.zeros(num_steps)
        time_stuck = 0
        burst_length = 2
        i = 0

        while(i < num_steps):
            chain = MarkovChain(self.proposal, self.constraints, accept, max_part[0], burst_length)
            for part in chain:
                part_score = self.score(part)

                if self._is_improvement(part_score, max_part[1]):
                    max_part = (part, part_score)
                    time_stuck = 0
                else:
                    time_stuck += 1

                i += 1
                if i >= num_steps:
                    break

            if time_stuck >= stuck_buffer * burst_length:
                burst_length *= 2

        return (max_part[0], observed_scores)

    def tilted_run(self, num_steps, p):
        """
        Preforms a tilted run.  A chain where the acceptance function always accepts better plans
        and accepts worse plans with some probabilty.

        :param `num_steps` (int): Total number of steps to take overall.
        :param `p` (float): The probability with which to accept worse scoring plans.

        :rtype (Partition * np.array): Tuple of maximal (or minimal) observed partition and a 1D
            numpy array of observed scores over each of the bursts.
        """
        chain = MarkovChain(self.proposal, self.constraints, self._titled_acceptance_function(p),
                            self.part, num_steps)
        max_part = (self.part, self.score(self.part))
        observed_scores = np.zeros(num_steps)

        for i, part in enumerate(chain):
            part_score = self.score(part)
            observed_scores[i] = part_score

            if self._is_improvement(part_score, max_part[1]):
                max_part = (part, part_score)

            self.tracking_fun(part)

        return (max_part[0], observed_scores)
