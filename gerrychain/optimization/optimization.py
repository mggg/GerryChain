from ..chain import MarkovChain
from ..partition import Partition
from ..accept import always_accept
import random
from typing import Union, Callable, List, Any
from tqdm import tqdm
import math


class SingleMetricOptimizer:
    """
    SingleMetricOptimizer represents the class of algorithms / chains that optimize plans with
    respect to a single metric.  An instance of this class encapsulates the following state
    information:
        * the dual graph and updaters via the initial partition,
        * the constraints new proposals are subject to,
        * the metric over which to optimize,
        * and whether or not to seek maximal or minimal values of the metric.

    The SingleMetricOptimizer class implements the following common methods of optimization:
        * Short Bursts
        * Simulated Annealing
        * Tilted Runs

    Both during and after a optimization run, the class properties `best_part` and `best_score`
    represent the optimal partition / corresponding score value observed.  Note that these
    properties do NOT persist across multiple optimization runs, as they are reset each time an
    optimization run is invoked.
    """

    def __init__(
        self,
        proposal: Callable[[Partition], Partition],
        constraints: Union[
            Callable[[Partition], bool], List[Callable[[Partition], bool]]
        ],
        initial_state: Partition,
        optimization_metric: Callable[[Partition], Any],
        maximize: bool = True,
        step_indexer: str = "step",
    ):
        """

        :param proposal: Function proposing the next state from the current state.
        :type proposal: Callable
        :param constraints: A function, or lists of functions, determining whether the proposed next
            state is valid (passes all binary constraints). Usually this is a
            :class:`~gerrychain.constraints.Validator` class instance.
        :type constraints: Union[Callable[[Partition], bool], List[Callable[[Partition], bool]]]
        :param initial_state: Initial state of the optimizer.
        :type initial_state: Partition
        :param optimization_metric: The score function with which to optimize over. This should have
            the signature: ``Partition -> 'a`` where 'a is comparable.
        :type optimization_metric: Callable[[Partition], Any]
        :param maximize: Boolean indicating whether to maximize or minimize the function. Defaults to True for maximize.
        :type maximize: bool, optional
        :param step_indexer: Name of the updater tracking the partitions step in the chain. If not
            implemented on the partition the constructor creates and adds it. Defaults to "step".
        :type step_indexer: str, optional



        :return: A SingleMetricOptimizer object
        :rtype: SingleMetricOptimizer
        """
        self._initial_part = initial_state
        self._proposal = proposal
        self._constraints = constraints
        self._score = optimization_metric
        self._maximize = maximize
        self._best_part = None
        self._best_score = None
        self._step_indexer = step_indexer

        if self._step_indexer not in self._initial_part.updaters:
            step_updater = lambda p: (
                0 if p.parent is None else p.parent[self._step_indexer] + 1
            )
            self._initial_part.updaters[self._step_indexer] = step_updater

    @property
    def best_part(self) -> Partition:
        """
        Partition object corresponding to best scoring plan observed over the current (or most
        recent) optimization run.

        :return: Partition object with the best score.
        :rtype: Partition
        """
        return self._best_part

    @property
    def best_score(self) -> Any:
        """
        Value of score metric corresponding to best scoring plan observed over the current (or most
        recent) optimization run.

        :return: Value of the best score.
        :rtype: Any
        """
        return self._best_score

    @property
    def score(self) -> Callable[[Partition], Any]:
        """
        The score function which is being optimized over.

        :return: The score function.
        :rtype: Callable[[Partition], Any]
        """
        return self._score

    def _is_improvement(self, new_score: float, old_score: float) -> bool:
        """
        Helper function defining improvement comparison between scores.  Scores can be any
        comparable type.

        :param new_score: Score of proposed partition.
        :type new_score: float
        :param old_score: Score of previous partition.
        :type old_score: float

        :return: Whether the new score is an improvement over the old score.
        :rtype: bool
        """
        if self._maximize:
            return new_score >= old_score
        else:
            return new_score <= old_score

    def _tilted_acceptance_function(self, p: float) -> Callable[[Partition], bool]:
        """
        Function factory that binds and returns a tilted acceptance function.

        :param p: The probability of accepting a worse score.
        :type p: float

        :return: An acceptance function for tilted chains.
        :rtype: Callable[[Partition], bool]
        """

        def tilted_acceptance_function(part):
            if part.parent is None:
                return True

            part_score = self.score(part)
            prev_score = self.score(part.parent)

            if self._is_improvement(part_score, prev_score):
                return True
            else:
                return random.random() < p

        return tilted_acceptance_function

    def _simulated_annealing_acceptance_function(
        self, beta_function: Callable[[int], float], beta_magnitude: float
    ):
        """
        Function factory that binds and returns a simulated annealing acceptance function.

        :param beta_function: Function (f: t -> beta, where beta is in [0,1]) defining temperature
            over time.  f(t) = 0 the chain is hot and every proposal is accepted.  At f(t) = 1 the
            chain is cold and worse proposal have a low probability of being accepted relative to
            the magnitude of change in score.
        :type beta_function: Callable[[int], float]
        :param beta_magnitude: Scaling parameter for how much to weight changes in score.
        :type beta_magnitude: float

        :return: A acceptance function for simulated annealing runs.
        :rtype: Callable[[Partition], bool]
        """

        def simulated_annealing_acceptance_function(part):
            if part.parent is None:
                return True
            score_delta = self.score(part) - self.score(part.parent)
            beta = beta_function(part[self._step_indexer])
            if self._maximize:
                score_delta *= -1
            return random.random() < math.exp(-beta * beta_magnitude * score_delta)

        return simulated_annealing_acceptance_function

    @classmethod
    def jumpcycle_beta_function(
        cls, duration_hot: int, duration_cold: int
    ) -> Callable[[int], float]:
        """
        Class method that binds and return simple hot-cold cycle beta temperature function, where
        the chain runs hot for some given duration and then cold for some duration, and repeats that
        cycle.

        :param duration_hot: Number of steps to run chain hot.
        :type duration_hot: int
        :param duration_cold: Number of steps to run chain cold.
        :type duration_cold: int

        :return: Beta function defining hot-cold cycle.
        :rtype: Callable[[int], float]
        """
        cycle_length = duration_hot + duration_cold

        def beta_function(step: int):
            time_in_cycle = step % cycle_length
            return float(time_in_cycle >= duration_hot)

        return beta_function

    @classmethod
    def linearcycle_beta_function(
        cls, duration_hot: int, duration_cooldown: int, duration_cold: int
    ) -> Callable[[int], float]:
        """
        Class method that binds and returns a simple linear hot-cool cycle beta temperature
        function, where the chain runs hot for some given duration, cools down linearly for some
        duration, and then runs cold for some duration before warming up again and repeating.

        :param duration_hot: Number of steps to run chain hot.
        :type duration_hot: int
        :param duration_cooldown: Number of steps needed to transition from hot to cold or
            vice-versa.
        :type duration_cooldown: int
        :param duration_cold: Number of steps to run chain cold.
        :type duration_cold: int

        :return: Beta function defining linear hot-cool cycle.
        :rtype: Callable[[int], float]
        """
        cycle_length = duration_hot + 2 * duration_cooldown + duration_cold

        def beta_function(step: int):
            time_in_cycle = step % cycle_length
            if time_in_cycle < duration_hot:
                return 0
            elif time_in_cycle < duration_hot + duration_cooldown:
                return (time_in_cycle - duration_hot) / duration_cooldown
            elif time_in_cycle < cycle_length - duration_cooldown:
                return 1
            else:
                return (
                    1
                    - (time_in_cycle - cycle_length + duration_cooldown)
                    / duration_cooldown
                )

        return beta_function

    @classmethod
    def linear_jumpcycle_beta_function(
        cls, duration_hot: int, duration_cooldown, duration_cold: int
    ):
        """
        Class method that binds and returns a simple linear hot-cool cycle beta temperature
        function, where the chain runs hot for some given duration, cools down linearly for some
        duration, and then runs cold for some duration before jumping back to hot and repeating.

        :param duration_hot: Number of steps to run chain hot.
        :type duration_hot: int
        :param duration_cooldown: Number of steps needed to transition from hot to cold.
        :type duration_cooldown: int
        :param duration_cold: Number of steps to run chain cold.
        :type duration_cold: int

        :return: Beta function defining linear hot-cool cycle.
        :rtype: Callable[[int], float]
        """
        cycle_length = duration_hot + duration_cooldown + duration_cold

        def beta_function(step: int):
            time_in_cycle = step % cycle_length
            if time_in_cycle < duration_hot:
                return 0
            elif time_in_cycle < duration_hot + duration_cooldown:
                return (time_in_cycle - duration_hot) / duration_cooldown
            else:
                return 1

        return beta_function

    @classmethod
    def logitcycle_beta_function(
        cls, duration_hot: int, duration_cooldown: int, duration_cold: int
    ) -> Callable[[int], float]:
        """
        Class method that binds and returns a logit hot-cool cycle beta temperature function, where
        the chain runs hot for some given duration, cools down according to the logit function

        :math:`f(x) = (log(x/(1-x)) + 5)/10`

        for some duration, and then runs cold for some duration before warming up again
        using the :math:`1-f(x)` and repeating.

        :param duration_hot: Number of steps to run chain hot.
        :type duration_hot: int
        :param duration_cooldown: Number of steps needed to transition from hot to cold or
            vice-versa.
        :type duration_cooldown: int
        :param duration_cold: Number of steps to run chain cold.
        :type duration_cold: int
        """
        cycle_length = duration_hot + 2 * duration_cooldown + duration_cold

        # this will scale from 0 to 1 approximately
        logit = lambda x: (math.log(x / (1 - x)) + 5) / 10

        def beta_function(step: int):
            time_in_cycle = step % cycle_length
            if time_in_cycle <= duration_hot:
                return 0
            elif time_in_cycle < duration_hot + duration_cooldown:
                value = logit((time_in_cycle - duration_hot) / duration_cooldown)
                if value < 0:
                    return 0
                if value > 1:
                    return 1
                return value
            elif time_in_cycle <= cycle_length - duration_cooldown:
                return 1
            else:
                value = 1 - logit(
                    (time_in_cycle - cycle_length + duration_cooldown)
                    / duration_cooldown
                )
                if value < 0:
                    return 0
                if value > 1:
                    return 1
                return value

        return beta_function

    @classmethod
    def logit_jumpcycle_beta_function(
        cls, duration_hot: int, duration_cooldown: int, duration_cold: int
    ) -> Callable[[int], float]:
        """
        Class method that binds and returns a logit hot-cool cycle beta temperature function, where
        the chain runs hot for some given duration, cools down according to the logit function

        :math:`f(x) = (log(x/(1-x)) + 5)/10`

        for some duration, and then runs cold for some duration before jumping back to hot and
        repeating.

        :param duration_hot: Number of steps to run chain hot.
        :type duration_hot: int
        :param duration_cooldown: Number of steps needed to transition from hot to cold or
            vice-versa.
        :type duration_cooldown: int
        :param duration_cold: Number of steps to run chain cold.
        :type duration_cold: int
        """
        cycle_length = duration_hot + duration_cooldown + duration_cold

        # this will scale from 0 to 1 approximately
        logit = lambda x: (math.log(x / (1 - x)) + 5) / 10

        def beta_function(step: int):
            time_in_cycle = step % cycle_length
            if time_in_cycle <= duration_hot:
                return 0
            elif time_in_cycle < duration_hot + duration_cooldown:
                value = logit((time_in_cycle - duration_hot) / duration_cooldown)
                if value < 0:
                    return 0
                if value > 1:
                    return 1
                return value
            else:
                return 1

        return beta_function

    def short_bursts(
        self,
        burst_length: int,
        num_bursts: int,
        accept: Callable[[Partition], bool] = always_accept,
        with_progress_bar: bool = False,
    ):
        """
        Performs a short burst run using the instance's score function. Each burst starts at the
        best performing plan of the previous burst. If there's a tie, the later observed one is
        selected.

        :param burst_length: Number of steps to run within each burst.
        :type burst_length: int
        :param num_bursts: Number of bursts to perform.
        :type num_bursts: int
        :param accept: Function accepting or rejecting the proposed state. Defaults to
            :func:`~gerrychain.accept.always_accept`.
        :type accept: Callable[[Partition], bool], optional
        :param with_progress_bar: Whether or not to draw tqdm progress bar. Defaults to False.
        :type with_progress_bar: bool, optional

        :return: Partition generator.
        :rtype: Generator[Partition]
        """
        if with_progress_bar:
            for part in tqdm(
                self.short_bursts(
                    burst_length, num_bursts, accept, with_progress_bar=False
                ),
                total=burst_length * num_bursts,
            ):
                yield part
            return

        self._best_part = self._initial_part
        self._best_score = self.score(self._best_part)

        for _ in range(num_bursts):
            chain = MarkovChain(
                self._proposal, self._constraints, accept, self._best_part, burst_length
            )

            for part in chain:
                yield part
                part_score = self.score(part)

                if self._is_improvement(part_score, self._best_score):
                    self._best_part = part
                    self._best_score = part_score

    def simulated_annealing(
        self,
        num_steps: int,
        beta_function: Callable[[int], float],
        beta_magnitude: float = 1,
        with_progress_bar: bool = False,
    ):
        """
        Performs simulated annealing with respect to the class instance's score function.

        :param num_steps: Number of steps to run for.
        :type num_steps: int
        :param beta_function: Function (f: t -> beta, where beta is in [0,1]) defining temperature
            over time.  f(t) = 0 the chain is hot and every proposal is accepted. At f(t) = 1 the
            chain is cold and worse proposal have a low probability of being accepted relative to
            the magnitude of change in score.
        :type beta_function: Callable[[int], float]
        :param beta_magnitude: Scaling parameter for how much to weight changes in score.
            Defaults to 1.
        :type beta_magnitude: float, optional
        :param with_progress_bar: Whether or not to draw tqdm progress bar. Defaults to False.
        :type with_progress_bar: bool, optional

        :return: Partition generator.
        :rtype: Generator[Partition]
        """
        chain = MarkovChain(
            self._proposal,
            self._constraints,
            self._simulated_annealing_acceptance_function(
                beta_function, beta_magnitude
            ),
            self._initial_part,
            num_steps,
        )

        self._best_part = self._initial_part
        self._best_score = self.score(self._best_part)

        chain_generator = tqdm(chain) if with_progress_bar else chain

        for part in chain_generator:
            yield part
            part_score = self.score(part)
            if self._is_improvement(part_score, self._best_score):
                self._best_part = part
                self._best_score = part_score

    def tilted_short_bursts(
        self,
        burst_length: int,
        num_bursts: int,
        p: float,
        with_progress_bar: bool = False,
    ):
        """
        Performs a short burst run using the instance's score function. Each burst starts at the
        best performing plan of the previous burst. If there's a tie, the later observed one is
        selected. Within each burst a tilted acceptance function is used where better scoring plans
        are always accepted and worse scoring plans are accepted with probability `p`.

        :param burst_length: Number of steps to run within each burst.
        :type burst_length: int
        :param num_bursts: Number of bursts to perform.
        :type num_bursts: int
        :param p: The probability of accepting a plan with a worse score.
        :type p: float
        :param with_progress_bar: Whether or not to draw tqdm progress bar. Defaults to False.
        :type with_progress_bar: bool, optional


        :return: Partition generator.
        :rtype: Generator[Partition]
        """
        return self.short_bursts(
            burst_length,
            num_bursts,
            accept=self._tilted_acceptance_function(p),
            with_progress_bar=with_progress_bar,
        )

    # TODO: Maybe add a max_time variable so we don't run forever.
    def variable_length_short_bursts(
        self,
        num_steps: int,
        stuck_buffer: int,
        accept: Callable[[Partition], bool] = always_accept,
        with_progress_bar: bool = False,
    ):
        """
        Performs a short burst where the burst length is allowed to increase as it gets harder to
        find high scoring plans. The initial burst length is set to 2, and it is doubled each time
        there is no improvement over the passed number (`stuck_buffer`) of runs.

        :param num_steps: Number of steps to run for.
        :type num_steps: int
        :param stuck_buffer: How many bursts of a given length with no improvement to allow before
            increasing the burst length.
        :type stuck_buffer: int
        :param accept: Function accepting or rejecting the proposed state. Defaults to :func:`~gerrychain.accept.always_accept`.
        :type accept: Callable[[Partition], bool], optional
        :param with_progress_bar: Whether or not to draw tqdm progress bar. Defaults to False.
        :type with_progress_bar: bool, optional

        :return: Partition generator.
        :rtype: Generator[Partition]
        """
        if with_progress_bar:
            for part in tqdm(
                self.variable_length_short_bursts(
                    num_steps, stuck_buffer, accept, with_progress_bar=False
                ),
                total=num_steps,
            ):
                yield part
            return

        self._best_part = self._initial_part
        self._best_score = self.score(self._best_part)
        time_stuck = 0
        burst_length = 2
        i = 0

        while i < num_steps:
            chain = MarkovChain(
                self._proposal, self._constraints, accept, self._best_part, burst_length
            )
            for part in chain:
                yield part
                part_score = self.score(part)
                if self._is_improvement(part_score, self._best_score):
                    self._best_part = part
                    self._best_score = part_score
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
        Performs a tilted run. A chain where the acceptance function always accepts better plans
        and accepts worse plans with some probability `p`.


        :param num_steps: Number of steps to run for.
        :type num_steps: int
        :param p: The probability of accepting a plan with a worse score.
        :type p: float
        :param with_progress_bar: Whether or not to draw tqdm progress bar. Defaults to False.
        :type with_progress_bar: bool, optional

        :return: Partition generator.
        :rtype: Generator[Partition]
        """
        chain = MarkovChain(
            self._proposal,
            self._constraints,
            self._tilted_acceptance_function(p),
            self._initial_part,
            num_steps,
        )

        self._best_part = self._initial_part
        self._best_score = self.score(self._best_part)

        chain_generator = tqdm(chain) if with_progress_bar else chain

        for part in chain_generator:
            yield part
            part_score = self.score(part)

            if self._is_improvement(part_score, self._best_score):
                self._best_part = part
                self._best_score = part_score
