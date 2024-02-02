from ..updaters import CountySplit
from .bounds import Bounds
import numpy
from typing import Callable, List, Dict
from ..partition import Partition


class Validator:
    """A single callable for checking that a partition passes a collection of
    constraints. Intended to be passed as the ``is_valid`` parameter when
    instantiating :class:`~gerrychain.MarkovChain`.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if all validators pass, and ``False`` if any one fails.

    Example usage::

        is_valid = Validator([constraint1, constraint2, constraint3])
        chain = MarkovChain(proposal, is_valid, accept, initial_state, total_steps)

    :ivar constraints: List of validator functions that will check partitions.
    :type constraints: List[Callable]
    """

    def __init__(self, constraints: List[Callable]) -> None:
        """
        :param constraints: List of validator functions that will check partitions.
        :type constraints: List[Callable]
        """
        self.constraints = constraints

    def __call__(self, partition: Partition) -> bool:
        """
        Determine if the given partition is valid.

        :param partition: The partition to check.
        :type partition: Partition
        """
        # check each constraint function and fail when a constraint test fails
        for constraint in self.constraints:
            is_valid = constraint(partition)
            # Coerce NumPy booleans
            if isinstance(is_valid, numpy.bool_):
                is_valid = bool(is_valid)

            if is_valid is False:
                return False
            elif is_valid is True:
                pass
            else:
                raise TypeError(
                    "Constraint {} returned a non-boolean.".format(repr(constraint))
                )

        # all constraints are satisfied
        return True

    def __repr__(self) -> str:
        constraint_names = [constraint.__name__ for constraint in self.constraints]
        return f"Validator(constraints={constraint_names})"


def within_percent_of_ideal_population(
    initial_partition: Partition, percent: float = 0.01, pop_key: str = "population"
) -> Bounds:
    """
    Require that all districts are within a certain percent of "ideal" (i.e.,
    uniform) population.

    Ideal population is defined as "total population / number of districts."

    :param initial_partition: Starting partition from which to compute district information.
    :type initial_partition: Partition
    :param percent: Allowed percentage deviation. Default is 1%.
    :type percent: float, optional
    :param pop_key: The name of the population
        :class:`Tally <gerrychain.updaters.Tally>`. Default is ``"population"``.
    :type pop_key: str, optional

    :returns: A :class:`.Bounds` constraint on the population attribute identified
        by ``pop_key``.
    :rtype: Bounds
    """

    def population(partition):
        return partition[pop_key].values()

    number_of_districts = len(initial_partition[pop_key].keys())
    total_population = sum(initial_partition[pop_key].values())
    ideal_population = total_population / number_of_districts
    bounds = ((1 - percent) * ideal_population, (1 + percent) * ideal_population)

    return Bounds(population, bounds=bounds)


def deviation_from_ideal(
    partition: Partition, attribute: str = "population"
) -> Dict[int, float]:
    """
    Computes the deviation of the given ``attribute`` from exact equality
    among parts of the partition. Usually ``attribute`` is the population, and
    this function is used to compute how far a districting plan is from exact population
    equality.

    By "deviation" we mean ``(actual_value - ideal)/ideal`` (not the absolute value).

    :param partition: A partition.
    :type partition: Partition
    :param attribute: The :class:`Tally <gerrychain.updaters.Tally>` to
        compute deviation for. Default is ``"population"``.
    :type attribute: str, optional

    :returns: dictionary from parts to their deviation
    :rtype: Dict[int, float]
    """
    number_of_districts = len(partition[attribute].keys())
    total = sum(partition[attribute].values())
    ideal = total / number_of_districts

    return {
        part: (value - ideal) / ideal for part, value in partition[attribute].items()
    }


def districts_within_tolerance(
    partition: Partition, attribute_name: str = "population", percentage: float = 0.1
) -> bool:
    """
    Check if all districts are within a certain percentage of the "smallest"
    district, as defined by the given attribute.

    :param partition: Partition class instance
    :type partition: Partition
    :param attrName: String that is the name of an updater in partition. Default is
        ``"population"``.
    :type attrName: str, optional
    :param percentage: What percent (as a number between 0 and 1) difference is allowed.
        Default is 0.1.
    :type percentage: float, optional

    :returns: Whether the districts are within specified tolerance
    :rtype: bool
    """
    if percentage >= 1:
        percentage *= 0.01

    values = partition[attribute_name].values()
    max_difference = max(values) - min(values)

    within_tolerance = max_difference <= percentage * min(values)
    return within_tolerance


def refuse_new_splits(partition_county_field: str) -> Callable[[Partition], bool]:
    """
    Refuse all proposals that split a county that was previous unsplit.

    :param partition_county_field: Name of field for county information generated by
        :func:`.county_splits`.
    :type partition_county_field: str

    :returns: Function that returns ``True`` if the proposal does not split any new counties.
    :rtype: Callable[[Partition], bool]
    """

    def _refuse_new_splits(partition: Partition) -> bool:
        for county_info in partition[partition_county_field].values():
            if county_info.split == CountySplit.NEW_SPLIT:
                return False

        return True

    return _refuse_new_splits


def no_vanishing_districts(partition: Partition) -> bool:
    """
    Require that no districts be completely consumed.

    :param partition: Partition to check.
    :type partition: Partition

    :returns: Whether no districts are completely consumed.
    :rtype: bool
    """
    if not partition.parent:
        return True
    return all(len(part) > 0 for part in partition.assignment.parts.values())
