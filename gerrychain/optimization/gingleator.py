import random
import warnings
from collections.abc import Hashable, Iterable
from functools import partial
from typing import Protocol

import numpy as np

from gerrychain.constraints import Validator, ConstraintFn
from gerrychain.partition import Partition
from gerrychain.proposals import ProposalFn

from .optimization import SingleMetricOptimizer


class GingleScoreFn(Protocol):
    def __call__(self, part: Partition, *, minority_perc_col: str, threshold: float) -> float: ...


class Gingleator(SingleMetricOptimizer):
    """
    `Gingleator` is a child class of `SingleMetricOptimizer` which can be used to search for plans
    with increased numbers of Gingles' districts.

    A gingles district (named for the Supreme Court case Thornburg v. Gingles) is a district
    that is majority-minority.  aka 50% + 1 of some population subgroup.  Demonstrating additional
    Gingles districts is one of the litmus tests used in bringing forth a VRA case.
    """

    def __init__(
        self,
        proposal: ProposalFn,
        constraints: ConstraintFn | Iterable[ConstraintFn] | Validator,
        initial_state: Partition,
        minority_perc_col: str | None = None,
        threshold: float = 0.5,
        score_function: GingleScoreFn | None = None,
        minority_pop_col: str | None = None,
        total_pop_col: str = "TOTPOP",
        min_perc_column_name: str = "_gingleator_auxiliary_helper_updater_min_perc_col",
        *,
        rng: random.Random | int | None = None,
    ) -> None:
        """Initialize a Gingleator instance.

        Args:
            proposal (Callable): Function proposing the next state from the current state.
            constraints (ConstraintFn | Iterable[ConstraintFn] | Validator): A function with
                signature ``Partition -> bool`` determining whether the proposed next state is
                valid (passes all binary constraints). Usually this is a Validator class
                instance.
            initial_state (Partition): Initial Partition class.
            minority_perc_col (str | None): The name of the updater mapping of district ids to
                the fraction of minority population within that district. If no updater is
                specified, one is made according to the ``min_perc_column_name`` parameter.
                Defaults to None.
            threshold (float, optional): Fraction beyond which to consider something a "Gingles"
                (or opportunity) district. Defaults to 0.5.
            score_function (GingleScoreFn | None): The function to use during optimization. This
                class provides several compatible class methods. Defaults to ``None``.
            minority_pop_col (str | None): If minority_perc_col is not defined, the minority
                population column with which to compute percentage. Defaults to None.
            total_pop_col (str, optional): If minority_perc_col is defined, the total population
                column with which to compute percentage. Defaults to "TOTPOP".
            min_perc_column_name (str, optional): If minority_perc_col is not defined, the name to
                give the created percentage updater. Defaults to
                "_gingleator_auxiliary_helper_updater_min_perc_col".
            rng (random.Random | int | None, optional): Source of randomness for the
                optimizer's internal chains; see
                :meth:`SingleMetricOptimizer.__init__ <gerrychain.optimization.SingleMetricOptimizer.__init__>`.
                Defaults to None.
        """
        if minority_perc_col is None and minority_pop_col is None:
            raise ValueError(
                "`minority_perc_col` and `minority_pop_col` cannot both be `None`. \
                              Unclear how to compute gingles district."
            )
        elif minority_perc_col is not None and minority_pop_col is not None:
            warnings.warn(
                "`minority_perc_col` and `minority_pop_col` are both specified. By \
                           default `minority_perc_col` will be used."
            )
        score_function = self.num_opportunity_dists if score_function is None else score_function

        if minority_perc_col is None:
            assert minority_pop_col is not None
            minority_population_column = minority_pop_col

            def minority_percentages(part: Partition) -> dict[Hashable, float]:
                return {
                    key: part[minority_population_column][key] / part[total_pop_col][key]
                    for key in part.parts
                }

            perc_up = {min_perc_column_name: minority_percentages}
            initial_state.updaters.update(perc_up)
            minority_perc_col = min_perc_column_name

        score = partial(score_function, minority_perc_col=minority_perc_col, threshold=threshold)

        super().__init__(proposal, constraints, initial_state, score, maximize=True, rng=rng)

    # ---------------------
    #    Score functions
    # ---------------------

    @classmethod
    def num_opportunity_dists(
        cls, part: Partition, minority_perc_col: str, threshold: float
    ) -> int:
        """Given a partition, returns the number of opportunity districts.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the
                fraction of minority population within that district.
            threshold (float): Fraction beyond which to consider something a "Gingles" (or
                opportunity) district.

        Returns:
            int: Number of opportunity districts.
        """
        dist_percs = part[minority_perc_col].values()
        return sum(list(map(lambda v: v >= threshold, dist_percs)))

    @classmethod
    def reward_partial_dist(
        cls, part: Partition, minority_perc_col: str, threshold: float
    ) -> float:
        """Return Number of opportunity districts + the percentage of the next highest district.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the
                fraction of minority population within that district.
            threshold (float): Fraction beyond which to consider something a "Gingles" (or
                opportunity) district.

        Returns:
            float: Number of opportunity districts + the percentage of the next highest district.
        """
        dist_percs = part[minority_perc_col].values()
        num_opport_dists = sum(list(map(lambda v: v >= threshold, dist_percs)))

        if num_opport_dists < len(dist_percs):
            next_dist = max(i for i in dist_percs if i < threshold)
        else:
            next_dist = 0

        return num_opport_dists + next_dist

    @classmethod
    def reward_next_highest_close(
        cls, part: Partition, minority_perc_col: str, threshold: float
    ) -> float:
        """Returns the number of opportunity districts + a scaled reward for the closest district.

        Given a partition, returns the number of opportunity districts, if no additional district
        is within 10% of reaching the threshold. If one is, the distance that district is from the
        threshold is scaled between 0 and 1 and added to the count of opportunity districts.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the
                fraction of minority population within that district.
            threshold (float): Fraction beyond which to consider something a "Gingles" (or
                opportunity) district.

        Returns:
            float: Number of opportunity districts + (next highest district - (threshold - 0.1)) *
                10
        """
        dist_percs = part[minority_perc_col].values()
        num_opport_dists = sum(list(map(lambda v: v >= threshold, dist_percs)))

        if num_opport_dists < len(dist_percs):
            next_dist = max(i for i in dist_percs if i < threshold)
        else:
            next_dist = 0

        if next_dist < threshold - 0.1:
            return num_opport_dists
        else:
            return num_opport_dists + (next_dist - threshold + 0.1) * 10

    @classmethod
    def penalize_maximum_over(
        cls, part: Partition, minority_perc_col: str, threshold: float
    ) -> float:
        """Returns the number of opportunity districts + (1 - the maximum excess) scaled to
        between 0 and 1.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the
                fraction of minority population within that district.
            threshold (float): Fraction beyond which to consider something a "Gingles" (or
                opportunity) district.

        Returns:
            float: Number of opportunity districts + (1 - the maximum excess) / (1 - threshold)
        """
        dist_percs = part[minority_perc_col].values()
        num_opportunity_dists = sum(list(map(lambda v: v >= threshold, dist_percs)))
        if num_opportunity_dists == 0:
            return 0
        else:
            max_dist = max(dist_percs)
            return num_opportunity_dists + (1 - max_dist) / (1 - threshold)

    @classmethod
    def penalize_avg_over(cls, part: Partition, minority_perc_col: str, threshold: float) -> float:
        """Returns the number of opportunity districts + (1 - the average excess) scaled to
        between 0 and 1.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the
                fraction of minority population within that district.
            threshold (float): Fraction beyond which to consider something a "Gingles" (or
                opportunity) district.

        Returns:
            float: Number of opportunity districts + (1 - the average excess)
        """
        dist_percs = part[minority_perc_col].values()
        opport_dists = list(filter(lambda v: v >= threshold, dist_percs))
        if opport_dists == []:
            return 0
        else:
            num_opportunity_dists = len(opport_dists)
            avg_opportunity_dist = np.mean(opport_dists)
            return float(num_opportunity_dists + (1 - avg_opportunity_dist) / (1 - threshold))
