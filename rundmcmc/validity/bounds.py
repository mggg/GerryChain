class Bounds:
    """
    Wrapper for numeric-validators to enforce upper and lower limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within set limits, and
    ``False`` otherwise.

    """

    def __init__(self, func, bounds):
        """
        :func: Numeric validator function. Should return an iterable of values.
        :bounds: Tuple of (lower, upper) numeric bounds.
        """
        self.func = func
        self.bounds = bounds

    def __call__(self, *args, **kwargs):
        lower, upper = self.bounds
        values = self.func(*args, **kwargs)
        return lower <= min(values) and max(values) <= upper

    @property
    def __name__(self):
        return "Bounds({})".format(self.func.__name__)


class UpperBound:
    """
    Wrapper for numeric-validators to enforce upper limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set upper limit,
    and ``False`` otherwise.

    """

    def __init__(self, func, bound):
        """
        :func: Numeric validator function. Should return a comparable value.
        :bounds: Comparable upper bound.
        """
        self.func = func
        self.bound = bound

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs) <= self.bound

    @property
    def __name__(self):
        return "UpperBound({})".format(self.func.__name__)


class LowerBound:
    """
    Wrapper for numeric-validators to enforce lower limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set lower limit,
    and ``False`` otherwise.

    """

    def __init__(self, func, bound):
        """
        :func: Numeric validator function. Should return a comparable value.
        :bounds: Comparable lower bound.
        """
        self.func = func
        self.bound = bound

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs) >= self.bound

    @property
    def __name__(self):
        return "LowerBound({})".format(self.func.__name__)


class SelfConfiguringUpperBound:
    """
    Wrapper for numeric-validators to enforce automatic upper limits.

    When instantiated, the initial upper bound is set as the initial value of
    the numeric-validator.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set upper limit,
    and ``False`` otherwise.

    """

    def __init__(self, func):
        """
        :func: Numeric validator function.
        """
        self.func = func
        self.bound = None

    def __call__(self, partition):
        if not self.bound:
            self.bound = self.func(partition)
            return self.__call__(partition)
        else:
            return self.func(partition) <= self.bound


class SelfConfiguringLowerBound:
    """
    Wrapper for numeric-validators to enforce automatic lower limits.

    When instantiated, the initial lower bound is set as the initial value of
    the numeric-validator minus some configurable ε.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set lower limit,
    and ``False`` otherwise.

    """

    def __init__(self, func, epsilon=0.05):
        """
        :func: Numeric validator function.
        :epsilon: Initial "wiggle room" that the validator allows.
        """
        self.func = func
        self.bound = None
        self.epsilon = epsilon
        self.__name__ = func.__name__

    def __call__(self, partition):
        if not self.bound:
            self.bound = self.func(partition) - self.epsilon
            return self.__call__(partition)
        else:
            return self.func(partition) >= self.bound


class WithinPercentRangeOfBounds:
    def __init__(self, func, percent):
        self.func = func
        self.percent = float(percent) / 100.
        self.lbound = None
        self.ubound = None

    def __call__(self, partition):
        if not (self.lbound and self.ubound):
            self.lbound = self.func(partition) * (1.0 - self.percent)
            self.ubound = self.func(partition) * (1.0 + self.percent)
            return True
        else:
            return self.lbound <= self.func(partition) <= self.ubound
