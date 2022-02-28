from .optimization import SingleMetricOptimizer

from functools import partial
import numpy as np
import warnings


class Gingleator(SingleMetricOptimizer):
    """
    `Gingleator` is a child class of `SingleMetricOptimizer` which can be used to search for plans
    with increased numbers of Gingles' districts.

    A gingles district (named for the Supreme Court case Thornburg v. Gingles) is a district that is
    majority-minority.  aka 50% + 1 of some population subgroup.  Demonstrating additional Gingles
    districts is one of the litmus test used in bringing forth a VRA case.
    """

    def __init__(self, proposal, constraints, initial_state,
                 minority_perc_col=None, threshold=0.5, score_function=None,
                 minority_pop_col=None, total_pop_col="TOTPOP",
                 min_perc_column_name="_gingleator_auxiliary_helper_updater_min_perc_col"):
        """
        :param `proposal`: Function proposing the next state from the current state.
        :param `constraints`: A function with signature ``Partition -> bool`` determining whether
            the proposed next state is valid (passes all binary constraints). Usually this is a
            :class:`~gerrychain.constraints.Validator` class instance.
        :param `initial_state`: Initial :class:`gerrychain.partition.Partition` class.
        :param `minority_perc_col`: Which updater is a mapping of district ids to the fraction of
            minority popultion within that district.
        :param `threshold`:  Beyond which fraction to consider something a "Gingles"
            (or opportunity) district.
        :param `score_function`: The function to using doing optimization.  Should have the
            signature ``Partition * str (minority_perc_col) * float (threshold) ->
            'a where 'a is Comparable``.  This class implement a few potential choices as class
            methods.
        :param `minority_pop_col`:  If minority_perc_col is defined, the minority population column
            with which to compute percentage.
        :param `total_pop_col`: If minority_perc_col is defined, the total population column with
            which to compute percentage.
        :param `min_perc_column_name`: If minority_perc_col is defined, the name to give the created
            percentage updater.
        """
        if minority_perc_col is None and minority_pop_col is None:
            raise ValueError("`minority_perc_col` and `minority_pop_col` cannot both be `None`. \
                              Unclear how to compute gingles district.")
        elif minority_perc_col is not None and minority_pop_col is not None:
            warnings.warn("`minority_perc_col` and `minority_pop_col` are both specified.  By \
                           default `minority_perc_col` will be used.")
        score_function = self.num_opportunity_dists if score_function is None else score_function

        if minority_perc_col is None:
            perc_up = {min_perc_column_name:
                            lambda part: {k: part[minority_pop_col][k] / part[total_pop_col][k]
                                          for k in part.parts.keys()}}
            initial_state.updaters.update(perc_up)
            minority_perc_col = min_perc_column_name

        score = partial(score_function, minority_perc_col=minority_perc_col, threshold=threshold)

        super().__init__(proposal, constraints, initial_state, score, maximize=True)

    """
    Score Functions
    """

    @classmethod
    def num_opportunity_dists(cls, part, minority_perc_col, threshold):
        """
        Given a partition, returns the number of opportunity districts.

        :param `part`: Partition to score.
        :param `minority_perc_col`: Which updater is a mapping of district ids to the fraction of
            minority popultion within that district.
        :param `threshold`: Beyond which fraction to consider something a "Gingles"
            (or opportunity) district.

        :rtype int
        """
        dist_percs = part[minority_perc_col].values()
        return sum(list(map(lambda v: v >= threshold, dist_percs)))

    @classmethod
    def reward_partial_dist(cls, part, minority_perc_col, threshold):
        """
        Given a partition, returns the number of opportunity districts + the percentage of the next
        highest district.

        :param `part`: Partition to score.
        :param `minority_perc_col`: Which updater is a mapping of district ids to the fraction of
            minority popultion within that district.
        :param `threshold`: Beyond which fraction to consider something a "Gingles"
            (or opportunity) district.

        :rtype float
        """
        dist_percs = part[minority_perc_col].values()
        num_opport_dists = sum(list(map(lambda v: v >= threshold, dist_percs)))
        next_dist = max(i for i in dist_percs if i < threshold)
        return num_opport_dists + next_dist

    @classmethod
    def reward_next_highest_close(cls, part, minority_perc_col, threshold):
        """
        Given a partition, returns the number of opportunity districts, if no additional district
        is within 10% of reaching the threshold. If one is, the distance that district is from the
        threshold is scaled between 0 and 1 and added to the count of opportunity districts.

        :param `part`: Partition to score.
        :param `minority_perc_col`: Which updater is a mapping of district ids to the fraction of
            minority popultion within that district.
        :param `threshold`: Beyond which fraction to consider something a "Gingles"
            (or opportunity) district.

        :rtype float
        """
        dist_percs = part[minority_perc_col].values()
        num_opport_dists = sum(list(map(lambda v: v >= threshold, dist_percs)))
        next_dist = max(i for i in dist_percs if i < threshold)

        if next_dist < threshold - 0.1:
            return num_opport_dists
        else:
            return num_opport_dists + (next_dist - threshold + 0.1) * 10

    @classmethod
    def penalize_maximum_over(cls, part, minority_perc_col, threshold):
        """
        Given a partition, returns the number of opportunity districts + (1 - the maximum excess)
        scaled to between 0 and 1.

        :param `part`: Partition to score.
        :param `minority_perc_col`: Which updater is a mapping of district ids to the fraction of
            minority popultion within that district.
        :param `threshold`: Beyond which fraction to consider something a "Gingles"
            (or opportunity) district.

        :rtype float
        """
        dist_percs = part[minority_perc_col].values()
        num_opportunity_dists = sum(list(map(lambda v: v >= threshold, dist_percs)))
        if num_opportunity_dists == 0:
            return 0
        else:
            max_dist = max(dist_percs)
            return num_opportunity_dists + (1 - max_dist) / (1 - threshold)

    @classmethod
    def penalize_avg_over(cls, part, minority_perc_col, threshold):
        """
        Given a partition, returns the number of opportunity districts + (1 - the average excess)
        scaled to between 0 and 1.

        :param `part`: Partition to score.
        :param `minority_perc_col`: Which updater is a mapping of district ids to the fraction of
            minority popultion within that district.
        :param `threshold`: Beyond which fraction to consider something a "Gingles"
            (or opportunity) district.

        :rtype float
        """
        dist_percs = part[minority_perc_col].values()
        opport_dists = list(filter(lambda v: v >= threshold, dist_percs))
        if opport_dists == []:
            return 0
        else:
            num_opportunity_dists = len(opport_dists)
            avg_opportunity_dist = np.mean(opport_dists)
            return num_opportunity_dists + (1 - avg_opportunity_dist) / (1 - threshold)
