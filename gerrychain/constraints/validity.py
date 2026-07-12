from collections.abc import Callable, Hashable, Iterable

import numpy

from ..partition import Partition
from ..updaters import CountySplit
from .bounds import Bounds


class Validator:
    """A single callable for checking that a partition passes a collection of
    constraints. Intended to be passed as the ``is_valid`` parameter when
    instantiating MarkovChain.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if all validators pass, and ``False`` if any one fails.

    Example usage::

        is_valid = Validator([constraint1, constraint2, constraint3])
        chain = MarkovChain(proposal, is_valid, accept, initial_state, total_steps)

    Attributes:
        constraints (list[Callable]): List of validator functions that will check partitions.
    """

    def __init__(self, constraints: Iterable[Callable[[Partition], bool]]) -> None:
        """Initialize a Validator instance.

        Args:
            constraints (list[Callable]): List of validator functions that will check partitions.

        """
        self.constraints = list(constraints)

    def __call__(self, partition: Partition) -> bool:
        """Determine if the given partition is valid.

        Args:
            partition (Partition): The partition to check.

        Returns:
            bool:
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
                raise TypeError(f"Constraint {repr(constraint)} returned a non-boolean.")

        # all constraints are satisfied
        return True

    def __repr__(self) -> str:
        constraint_names = [
            getattr(constraint, "__name__", type(constraint).__name__)
            for constraint in self.constraints
        ]
        return f"Validator(constraints={constraint_names})"


def within_percent_of_ideal_population(
    initial_partition: Partition, percent: float = 0.01, pop_key: str = "population"
) -> Bounds[[Partition]]:
    """Construct a bounds object to ensure all districts are closed to a target population.

    Args:
        initial_partition (Partition): Starting partition from which to compute district
            information.
        percent (float, optional): Allowed percentage deviation. Default is 1%.
        pop_key (str, optional): The name of the population Tally. Default is ``"population"``.

    Returns:
        Bounds: A Bounds constraint on the population attribute identified by
            ``pop_key``.
    """

    def population(partition: Partition) -> Iterable[float]:
        return partition[pop_key].values()

    number_of_districts = len(initial_partition[pop_key].keys())
    total_population = sum(initial_partition[pop_key].values())
    ideal_population = total_population / number_of_districts
    bounds = ((1 - percent) * ideal_population, (1 + percent) * ideal_population)

    return Bounds(population, bounds=bounds)


def deviation_from_ideal(
    partition: Partition, attribute: str = "population"
) -> dict[Hashable, float]:
    """Determine the deviation of the given attribute from the ideal value
    among parts of the partition.

    Computes the deviation of the given ``attribute`` from exact equality among parts of the
    partition. Usually ``attribute`` is the population, and this function is used to compute how
    far a districting plan is from exact population equality.

    By "deviation" we mean ``(actual_value - ideal)/ideal`` (not the absolute value).

    Args:
        partition (Partition): A partition.
        attribute (str, optional): The Tally to compute
            deviation for. Default is ``"population"``.

    Returns:
        dict[Hashable, float]: dictionary from parts to their deviation
    """
    number_of_districts = len(partition[attribute].keys())
    total = sum(partition[attribute].values())
    ideal = total / number_of_districts

    return {part: (value - ideal) / ideal for part, value in partition[attribute].items()}


def districts_within_tolerance(
    partition: Partition, attribute_name: str = "population", percentage: float = 0.1
) -> bool:
    """Return whether the districts are within specified tolerance.

    Check if all districts are within a certain percentage of the "smallest" district, as defined
    by the given attribute. For example, if the attribute is population, this function checks if
    all districts are within a certain percentage of the smallest population district.

    Args:
        partition (Partition): Partition class instance
        attribute_name (str, optional): Name of an updater in ``partition``. Defaults to
            ``"population"``.
        percentage (float, optional): What percent (as a number between 0 and 1) difference is
            allowed. Default is 0.1.

    Returns:
        bool: Whether the districts are within specified tolerance
    """
    if percentage >= 1:
        percentage *= 0.01

    values = partition[attribute_name].values()
    max_difference = max(values) - min(values)

    within_tolerance = max_difference <= percentage * min(values)
    return within_tolerance


def refuse_new_splits(partition_county_field: str) -> Callable[[Partition], bool]:
    """Refuse all proposals that split a county that was previous unsplit.

    This function refuse all proposals that split a county that was previous unsplit. It returns
    function that returns ``True`` if the proposal does not split any new counties.

    Args:
        partition_county_field (str): Name of field for county information generated by
            `county_splits`.

    Returns:
        Callable[[Partition], bool]: Function that returns ``True`` if the proposal does not split
            any new counties.
    """

    def _refuse_new_splits(partition: Partition) -> bool:
        for county_info in partition[partition_county_field].values():
            if county_info.split == CountySplit.NEW_SPLIT:
                return False

        return True

    return _refuse_new_splits


def no_vanishing_districts(partition: Partition) -> bool:
    """Require that no districts be completely consumed. Can happen in flip proposal.

    Args:
        partition (Partition): Partition to check.

    Returns:
        bool: Whether no districts are completely consumed.
    """
    if not partition.parent:
        return True
    return all(len(part) > 0 for part in partition.assignment.parts.values())
