from ..chain import MarkovChain
from .. partition import Partition
from ..accept import always_accept
from ..random import random

from typing import Union, Callable, List, Any
from tqdm import tqdm

class SingleMetricOptimizer:
    """
    SingleMetricOptimizer represents the class of algorithms / chains that optimize plans with
    respect to a single metric.  This class implements some common methods of optimization.
    """

    def __init__(self, proposal: Callable[[Partition], Partition], constraints: Union[Callable[[Partition], bool], List[Callable[[Partition], bool]]],
                 initial_state: Partition, optimization_metric: Callable[[Partition], Any], maximize: bool = True):
        """
        :param `proposal`: Function proposing the next state from the current state.
        :param `constraints`: A function with signature ``Partition -> bool`` determining whether
            the proposed next state is valid (passes all binary constraints). Usually this is a
            :class:`~gerrychain.constraints.Validator` class instance.
        :param `initial_state`: Initial :class:`gerrychain.partition.Partition` class.
        :param `optimization_metric`: The score function with which to optimize over.  This should
            have the signature: ``Partition -> 'a where 'a is Comparable``
        :param `maximize` (bool): Whether to minimize or maximize the function?
        """
        self.initial_part = initial_state
        self.proposal = proposal
        self.constraints = constraints
        self.score = optimization_metric
        self.maximize = maximize
        self.best_part = None
        self.best_score = None

    def _is_improvement(self, part_score, max_score) -> bool:
        if self.maximize:
            return part_score >= max_score
        else:
            return part_score <= max_score

    def short_bursts(self, burst_length: int, num_bursts: int, 
                     accept: Callable[[Partition], bool] = always_accept, with_progress_bar: bool = False):
        """
        Preforms a short burst run using the instance's score function.  Each burst starts at the
        best preforming plan of the previous burst.  If there's a tie, the later observed one is
        selected.

        :param `burst_length` (int): How many steps to run within each burst?
        :param `num_bursts` (int): How many bursts to preform?
        :param `accept`: Function accepting or rejecting the proposed state. In the most basic
            use case, this always returns ``True``.

        :rtype (Partition * np.array): Tuple of maximal (or minimal) observed partition and a 2D
            numpy array of observed scores over each of the bursts.
        """
        if with_progress_bar:
            tqdm(self.short_bursts(burst_length, num_bursts, accept, with_progress_bar=False),
                 total=burst_length*num_bursts)
            return

        self.best_part = self.initial_part
        self.best_score = self.score(self.best_part)

        for i in range(num_bursts):
            chain = MarkovChain(self.proposal, self.constraints, accept, self.best_part, burst_length)

            for part in chain:
                yield part
                part_score = self.score(part)

                if self._is_improvement(part_score, self.best_score):
                    self.best_part = part
                    self.best_score = part_score


    def _titled_acceptance_function(self, p: float) -> Callable[[Partition], bool]:
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

    def tilted_short_bursts(self, burst_length: int, num_bursts: int, p: float, with_progress_bar: bool = False):
        """
        Preforms a short burst run using the instance's score function.  Each burst starts at the
        best preforming plan of the previous burst.  If there's a tie, the later observed one is
        selected.  Within each burst a tilted acceptance function is used where better scoring plans
        are always accepted and worse scoring plans are accepted with probability `p`.

        :param `burst_length` (int): How many steps to run within each burst?
        :param `num_bursts` (int): How many bursts to preform?
        :param `p` (float): The probability with which to accept worse scoring plans.

        :rtype (Partition * np.array): Tuple of maximal (or minimal) observed partition and a 2D
            numpy array of observed scores over each of the bursts.
        """
        return self.short_bursts(burst_length, num_bursts, accept=self._titled_acceptance_function(p),
                                 with_progress_bar=with_progress_bar)

    def variable_lenght_short_bursts(self, num_steps: int , stuck_buffer: int, 
                                     accept: Callable[[Partition], bool] = always_accept,
                                     with_progress_bar: bool = False):
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
        if with_progress_bar:
            tqdm(self.variable_lenght_short_bursts(num_steps, stuck_buffer, accept, with_progress_bar=False),
                 total=num_steps)
            return
        
        self.best_part = self.initial_part
        self.best_score = self.score(self.best_part)
        time_stuck = 0
        burst_length = 2
        i = 0

        while(i < num_steps):
            chain = MarkovChain(self.proposal, self.constraints, accept, self.best_part, burst_length)
            for part in chain:
                yield part
                part_score = self.score(part)
                if self._is_improvement(part_score, self.best_score):
                    self.best_part = part
                    self.best_score = part_score
                    time_stuck = 0
                else:
                    time_stuck += 1

                i += 1
                if i >= num_steps:
                    break

            if time_stuck >= stuck_buffer * burst_length:
                burst_length *= 2

    def tilted_run(self, num_steps: int, p: float, with_progress_bar: bool = False):
        """
        Preforms a tilted run.  A chain where the acceptance function always accepts better plans
        and accepts worse plans with some probabilty.

        :param `num_steps` (int): Total number of steps to take overall.
        :param `p` (float): The probability with which to accept worse scoring plans.

        :rtype (Partition * np.array): Tuple of maximal (or minimal) observed partition and a 1D
            numpy array of observed scores over each of the bursts.
        """
        chain = MarkovChain(self.proposal, self.constraints, self._titled_acceptance_function(p),
                            self.initial_part, num_steps)
        
        self.best_part = self.initial_part
        self.best_score = self.score(self.best_part)

        chain_enumerator = tqdm(enumerate(chain)) if with_progress_bar else enumerate(chain)

        for i, part in chain_enumerator:
            yield part
            part_score = self.score(part)

            if self._is_improvement(part_score, self.best_score):
                    self.best_part = part
                    self.best_score = part_score

