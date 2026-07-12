from collections.abc import Callable, Iterable
from typing import Generic, ParamSpec

from ..partition import Partition

P = ParamSpec("P")


class Bounds(Generic[P]):
    """
    Wrapper for numeric-validators to enforce upper and lower limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within set limits, and
    ``False`` otherwise.

    """

    def __init__(self, func: Callable[P, Iterable[float]], bounds: tuple[float, float]) -> None:
        """Initialize a Bounds instance.

        This initializer sets up `Bounds` with the provided arguments and validates required state.

        Args:
            func (Callable): Numeric validator function. Should return an iterable of values.
            bounds (tuple[float, float]): Tuple of (lower, upper) numeric bounds.

        """
        self.func = func
        self.bounds = bounds

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> bool:
        lower, upper = self.bounds
        values = self.func(*args, **kwargs)
        return lower <= min(values) and max(values) <= upper

    @property
    def __name__(self) -> str:
        return f"Bounds({getattr(self.func, '__name__', type(self.func).__name__)},{self.bounds})"

    def __repr__(self) -> str:
        return f"<{self.__name__}>"


class UpperBound(Generic[P]):
    """
    Wrapper for numeric-validators to enforce upper limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set upper limit,
    and ``False`` otherwise.
    """

    def __init__(self, func: Callable[P, float], bound: float) -> None:
        """Initialize a UpperBound instance.

        This initializer sets up `UpperBound` with the provided arguments and validates required
        state.

        Args:
            func (Callable): Numeric validator function. Should return a comparable value.
            bound (float): Comparable upper bound.

        """
        self.func = func
        self.bound = bound

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> bool:
        return self.func(*args, **kwargs) <= self.bound

    @property
    def __name__(self) -> str:
        return f"UpperBound({getattr(self.func, '__name__', type(self.func).__name__)} >= {self.bound})"

    def __repr__(self) -> str:
        return f"<{self.__name__}>"


class LowerBound(Generic[P]):
    """
    Wrapper for numeric-validators to enforce lower limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set lower limit,
    and ``False`` otherwise.
    """

    def __init__(self, func: Callable[P, float], bound: float) -> None:
        """Initialize a LowerBound instance.

        This initializer sets up `LowerBound` with the provided arguments and validates required
        state.

        Args:
            func (Callable): Numeric validator function. Should return a comparable value.
            bound (float): Comparable lower bound.

        """
        self.func = func
        self.bound = bound

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> bool:
        return self.func(*args, **kwargs) >= self.bound

    @property
    def __name__(self) -> str:
        return f"LowerBound({getattr(self.func, '__name__', type(self.func).__name__)} <= {self.bound})"

    def __repr__(self) -> str:
        return f"<{self.__name__}>"


class SelfConfiguringUpperBound:
    """
    Wrapper for numeric-validators to enforce automatic upper limits.

    When instantiated, the initial upper bound is set as the initial value of
    the numeric-validator.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set upper limit,
    and ``False`` otherwise.
    """

    def __init__(self, func: Callable[[Partition], float]) -> None:
        """Initialize a SelfConfiguringUpperBound instance.

        This initializer sets up `SelfConfiguringUpperBound` with the provided arguments and
        validates required state.

        Args:
            func (Callable): Numeric validator function.

        """
        self.func = func
        self.bound = None

    def __call__(self, partition: Partition) -> bool:
        if not self.bound:
            self.bound = self.func(partition)
        return self.func(partition) <= self.bound

    @property
    def __name__(self) -> str:
        return (
            f"SelfConfiguringUpperBound({getattr(self.func, '__name__', type(self.func).__name__)})"
        )

    def __repr__(self) -> str:
        return f"<{self.__name__}>"


class SelfConfiguringLowerBound:
    """
    Wrapper for numeric-validators to enforce automatic lower limits.

    When instantiated, the initial lower bound is set as the initial value of
    the numeric-validator minus some configurable ε.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set lower limit,
    and ``False`` otherwise.
    """

    def __init__(self, func: Callable[[Partition], float], epsilon: float = 0.05) -> None:
        """Initialize a SelfConfiguringLowerBound instance.

        This initializer sets up `SelfConfiguringLowerBound` with the provided arguments and
        validates required state.

        Args:
            func (Callable): Numeric validator function.
            epsilon (float, optional): Initial population deviation allowable by the validator as a
                percentage of the ideal population. Defaults to 0.05.

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
        return (
            f"SelfConfiguringLowerBound({getattr(self.func, '__name__', type(self.func).__name__)})"
        )

    def __repr__(self) -> str:
        return f"<{self.__name__}>"


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

    def __init__(self, func: Callable[[Partition], float], percent: float) -> None:
        """Initialize a WithinPercentRangeOfBounds instance.

        This initializer sets up `WithinPercentRangeOfBounds` with the provided arguments and
        validates required state.

        Args:
            func (Callable): Numeric validator function.
            percent (float): Percentage of the initial value to use as the bounds.

        Warning:
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
        return f"WithinPercentRangeOfBounds({getattr(self.func, '__name__', type(self.func).__name__)})"

    def __repr__(self) -> str:
        return f"<{self.__name__}>"
