from typing import Callable, Tuple
from ..partition import Partition


class Bounds:
    """
    Wrapper for numeric-validators to enforce upper and lower limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within set limits, and
    ``False`` otherwise.

    """

    def __init__(self, func: Callable, bounds: Tuple[float, float]) -> None:
        """
        :param func: Numeric validator function. Should return an iterable of values.
        :type func: Callable
        :param bounds: Tuple of (lower, upper) numeric bounds.
        :type bounds: Tuple[float, float]
        """
        self.func = func
        self.bounds = bounds

    def __call__(self, *args, **kwargs) -> bool:
        lower, upper = self.bounds
        values = self.func(*args, **kwargs)
        return lower <= min(values) and max(values) <= upper

    @property
    def __name__(self) -> str:
        return "Bounds({},{})".format(self.func.__name__, str(self.bounds))

    def __repr__(self) -> str:
        return "<{}>".format(self.__name__)


class UpperBound:
    """
    Wrapper for numeric-validators to enforce upper limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set upper limit,
    and ``False`` otherwise.
    """

    def __init__(self, func: Callable, bound: float) -> None:
        """
        :param func: Numeric validator function. Should return a comparable value.
        :type func: Callable
        :param bounds: Comparable upper bound.
        :type bounds: float
        """
        self.func = func
        self.bound = bound

    def __call__(self, *args, **kwargs) -> bool:
        return self.func(*args, **kwargs) <= self.bound

    @property
    def __name__(self) -> str:
        return "UpperBound({} >= {})".format(self.func.__name__, self.bound)

    def __repr__(self) -> str:
        return "<{}>".format(self.__name__)


class LowerBound:
    """
    Wrapper for numeric-validators to enforce lower limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set lower limit,
    and ``False`` otherwise.
    """

    def __init__(self, func: Callable, bound: float) -> None:
        """
        :param func: Numeric validator function. Should return a comparable value.
        :type func: Callable
        :param bounds: Comparable lower bound.
        :type bounds: float
        """
        self.func = func
        self.bound = bound

    def __call__(self, *args, **kwargs) -> bool:
        return self.func(*args, **kwargs) >= self.bound

    @property
    def __name__(self) -> str:
        return "LowerBound({} <= {})".format(self.func.__name__, self.bound)

    def __repr__(self) -> str:
        return "<{}>".format(self.__name__)


class SelfConfiguringUpperBound:
    """
    Wrapper for numeric-validators to enforce automatic upper limits.

    When instantiated, the initial upper bound is set as the initial value of
    the numeric-validator.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set upper limit,
    and ``False`` otherwise.
    """

    def __init__(self, func: Callable) -> None:
        """
        :param func: Numeric validator function.
        :type func: Callable
        """
        self.func = func
        self.bound = None

    def __call__(self, partition: Partition) -> bool:
        if not self.bound:
            self.bound = self.func(partition)
        return self.func(partition) <= self.bound

    @property
    def __name__(self) -> str:
        return "SelfConfiguringUpperBound({})".format(self.func.__name__)

    def __repr__(self) -> str:
        return "<{}>".format(self.__name__)


class SelfConfiguringLowerBound:
    """
    Wrapper for numeric-validators to enforce automatic lower limits.

    When instantiated, the initial lower bound is set as the initial value of
    the numeric-validator minus some configurable ε.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set lower limit,
    and ``False`` otherwise.
    """

    def __init__(self, func: Callable, epsilon: float = 0.05) -> None:
        """
        :param func: Numeric validator function.
        :type func: Callable
        :param epsilon: Initial population deviation allowable by the validator
            as a percentage of the ideal population. Defaults to 0.05.
        :type epsilon: float, optional
        """
        self.func = func
        self.bound = None
        self.epsilon = epsilon

    def __call__(self, partition: Partition) -> bool:
        if not self.bound:
            self.bound = self.func(partition) - self.epsilon
        return self.func(partition) >= self.bound

    @property
    def __name__(self) -> str:
        return "SelfConfiguringLowerBound({})".format(self.func.__name__)

    def __repr__(self) -> str:
        return "<{}>".format(self.__name__)


class WithinPercentRangeOfBounds:
    """
    Wrapper for numeric-validators to enforce upper and lower limits
    determined by a percentage of the initial value.

    When instantiated, the initial upper and lower bounds are set as the
    initial value of the numeric-validator times (1 ± percent).

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within the desired
    percentage range of the initial value, and ``False`` otherwise.
    """

    def __init__(self, func: Callable, percent: float) -> None:
        """
        :param func: Numeric validator function.
        :type func: Callable
        :param percent: Percentage of the initial value to use as the bounds.
        :type percent: float

        :returns: None

        .. Warning::
            The percentage is assumed to be in the range [0.0, 100.0].
        """
        self.func = func
        self.percent = float(percent) / 100.0
        self.lbound = None
        self.ubound = None

    def __call__(self, partition: Partition) -> bool:
        if not (self.lbound and self.ubound):
            self.lbound = self.func(partition) * (1.0 - self.percent)
            self.ubound = self.func(partition) * (1.0 + self.percent)
            return True
        else:
            return self.lbound <= self.func(partition) <= self.ubound

    @property
    def __name__(self) -> str:
        return "WithinPercentRangeOfBounds({})".format(self.func.__name__)

    def __repr__(self) -> str:
        return "<{}>".format(self.__name__)
