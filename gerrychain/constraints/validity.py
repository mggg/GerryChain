from collections.abc import Callable, Hashable, Iterable, Mapping
from numbers import Integral

import numpy

from ..partition import Partition
from ..updaters import CountySplit
from .bounds import Bounds

# A single binary constraint: takes a Partition and returns whether it is valid.
ConstraintFn = Callable[[Partition], bool]


class Validator:
    """A single callable that bundles a collection of constraint functions.

    This is a callable class used to check partition satisfies a set of constraints, and it is
    intended to be passed as the ``constraints`` parameter when instantiating a MarkovChain.


    Example usage::

        validator = Validator([constraint1, constraint2, constraint3])
        chain = MarkovChain(proposal, validator, accept, initial_partition, total_steps)

    Attributes:
        constraints (list[ConstraintFn]): List of constraint functions that will check partitions.
    """

    def __init__(self, constraints: Iterable[ConstraintFn]) -> None:
        """Initialize a Validator instance.

        Args:
            constraints (Iterable[ConstraintFn]): Constraint functions that will check partitions.

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


def within_percent_of_ideal_population_per_member(
    initial_partition: Partition,
    members_per_district: Mapping[Hashable, int],
    percent: float = 0.01,
    pop_key: str = "population",
) -> Bounds[[Partition]]:
    """Bound each district's population per member around the plan-wide ideal.

    The ideal population is the total population divided by the total number of members. Member
    counts are copied when the constraint is constructed, so they remain fixed to district labels.

    Args:
        initial_partition (Partition): Starting partition used to compute the ideal population.
        members_per_district (Mapping[Hashable, int]): Positive member count for every district.
        percent (float, optional): Allowed percentage deviation. Default is 1%.
        pop_key (str, optional): The name of the population Tally. Default is ``"population"``.

    Returns:
        Bounds: A Bounds constraint on each district's population divided by its member count.
    """
    if not members_per_district:
        raise ValueError("members_per_district must not be empty.")

    members: dict[Hashable, int] = {}
    for part, member_count in members_per_district.items():
        if isinstance(member_count, bool) or not isinstance(member_count, Integral):
            raise ValueError(
                f"Member count for district {part!r} must be a positive integer; "
                f"got {member_count!r}."
            )
        if member_count <= 0:
            raise ValueError(
                f"Member count for district {part!r} must be a positive integer; "
                f"got {member_count!r}."
            )
        members[part] = int(member_count)

    populations = initial_partition[pop_key]
    missing = [part for part in populations if part not in members]
    unexpected = [part for part in members if part not in populations]
    if missing or unexpected:
        raise ValueError(
            "members_per_district keys must match the partition labels exactly; "
            f"missing={missing!r}, unexpected={unexpected!r}."
        )

    def population_per_member(partition: Partition) -> Iterable[float]:
        return [population / members[part] for part, population in partition[pop_key].items()]

    ideal_population = sum(populations.values()) / sum(members.values())
    bounds = ((1 - percent) * ideal_population, (1 + percent) * ideal_population)

    return Bounds(population_per_member, bounds=bounds)


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


def refuse_new_splits(partition_county_field: str) -> ConstraintFn:
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
