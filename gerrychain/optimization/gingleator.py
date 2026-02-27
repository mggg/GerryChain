import warnings
from functools import partial
from typing import Callable, Iterable, Optional, Union

import numpy as np

from gerrychain.constraints import Bounds, Validator
from gerrychain.partition import Partition

from .optimization import SingleMetricOptimizer


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
        proposal: Callable,
        constraints: Union[Iterable[Callable], Validator, Iterable[Bounds], Callable],
        initial_state: Partition,
        minority_perc_col: Optional[str] = None,
        threshold: float = 0.5,
        score_function: Optional[Callable] = None,
        minority_pop_col: Optional[str] = None,
        total_pop_col: str = "TOTPOP",
        min_perc_column_name: str = "_gingleator_auxiliary_helper_updater_min_perc_col",
    ):
        """
        Args:
            proposal (Callable): Function proposing the next state from the current state.
            constraints (Union[Iterable[Callable], Validator, Iterable[Bounds], Callable]): A
                function with signature ``Partition -> bool`` determining whether the proposed next
                state is valid (passes all binary constraints). Usually this is a
                :class:`~gerrychain.constraints.Validator` class instance.
            initial_state (Partition): Initial :class:`gerrychain.partition.Partition` class.
            minority_perc_col (Optional[str]): The name of the updater mapping of district ids to
                the fraction of minority population within that district. If no updater is
                specified, one is made according to the ``min_perc_column_name`` parameter. Defaults
                to None.
            threshold (float, optional): Fraction beyond which to consider something a "Gingles" (or
                opportunity) district. Defaults to 0.5.
            score_function (Optional[Callable]): The function to use during optimization. Should
                have the signature ``Partition * str (minority_perc_col) * float (threshold) -> 'a
                where 'a is Comparable``. This class implements a few potential choices as class
                methods. Defaults to None.
            minority_pop_col (Optional[str]): If minority_perc_col is not defined, the minority
                population column with which to compute percentage. Defaults to None.
            total_pop_col (str, optional): If minority_perc_col is defined, the total population
                column with which to compute percentage. Defaults to "TOTPOP".
            min_perc_column_name (str, optional): If minority_perc_col is not defined, the name to
                give the created percentage updater. Defaults to
                "_gingleator_auxiliary_helper_updater_min_perc_col".
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
            perc_up = {
                min_perc_column_name: lambda part: {
                    k: part[minority_pop_col][k] / part[total_pop_col][k] for k in part.parts.keys()
                }
            }
            initial_state.updaters.update(perc_up)
            minority_perc_col = min_perc_column_name

        score = partial(score_function, minority_perc_col=minority_perc_col, threshold=threshold)

        super().__init__(proposal, constraints, initial_state, score, maximize=True)

    # ---------------------
    #    Score functions
    # ---------------------

    @classmethod
    def num_opportunity_dists(
        cls, part: Partition, minority_perc_col: str, threshold: float
    ) -> int:
        """
        Given a partition, returns the number of opportunity districts.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the fraction
                of minority population within that district.
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
        """
        Given a partition, returns the number of opportunity districts + the percentage of the next
        highest district.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the fraction
                of minority population within that district.
            threshold (float): Fraction beyond which to consider something a "Gingles" (or
                opportunity) district.

        Returns:
            float: Number of opportunity districts + the percentage of the next highest district.
        """
        dist_percs = part[minority_perc_col].values()
        num_opport_dists = sum(list(map(lambda v: v >= threshold, dist_percs)))
        next_dist = max(i for i in dist_percs if i < threshold)
        return num_opport_dists + next_dist

    @classmethod
    def reward_next_highest_close(cls, part: Partition, minority_perc_col: str, threshold: float):
        """
        Given a partition, returns the number of opportunity districts, if no additional district
        is within 10% of reaching the threshold. If one is, the distance that district is from the
        threshold is scaled between 0 and 1 and added to the count of opportunity districts.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the fraction
                of minority population within that district.
            threshold (float): Fraction beyond which to consider something a "Gingles" (or
                opportunity) district.

        Returns:
            float: Number of opportunity districts + (next highest district - (threshold - 0.1)) *
                10
        """
        dist_percs = part[minority_perc_col].values()
        num_opport_dists = sum(list(map(lambda v: v >= threshold, dist_percs)))
        next_dist = max(i for i in dist_percs if i < threshold)

        if next_dist < threshold - 0.1:
            return num_opport_dists
        else:
            return num_opport_dists + (next_dist - threshold + 0.1) * 10

    @classmethod
    def penalize_maximum_over(cls, part: Partition, minority_perc_col: str, threshold: float):
        """
        Given a partition, returns the number of opportunity districts + (1 - the maximum excess)
        scaled to between 0 and 1.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the fraction
                of minority population within that district.
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
    def penalize_avg_over(cls, part: Partition, minority_perc_col: str, threshold: float):
        """
        Given a partition, returns the number of opportunity districts + (1 - the average excess)
        scaled to between 0 and 1.

        Args:
            part (Partition): Partition to score.
            minority_perc_col (str): The name of the updater mapping of district ids to the fraction
                of minority population within that district.
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
            return num_opportunity_dists + (1 - avg_opportunity_dist) / (1 - threshold)
