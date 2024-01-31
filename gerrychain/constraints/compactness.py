from ..partition import Partition
import math


from .bounds import SelfConfiguringLowerBound, SelfConfiguringUpperBound


def L1_reciprocal_polsby_popper(partition: Partition) -> float:
    """
    Returns the :math:`L^1` norm of the reciprocal Polsby-Popper scores
    for the given partition

    :param partition: Partition representing a districting plan
    :type partition: Partition

    :returns: :math:`L^1` norm of the reciprocal Polsby-Popper scores
    :rtype: float
    """
    return sum(1 / value for value in partition["polsby_popper"].values())


def L1_polsby_popper(partition: Partition) -> float:
    """
    Returns the :math:`L^1` norm of the Polsby-Popper scores
    for the given partition

    :param partition: Partition representing a districting plan
    :type partition: Partition

    :returns: :math:`L^1` norm of the reciprocal Polsby-Popper scores
    :rtype: float
    """
    return sum(value for value in partition["polsby_popper"].values())


def L2_polsby_popper(partition: Partition) -> float:
    """
    Returns the :math:`L^2` norm of the Polsby-Popper scores
    for the given partition.

    :param partition: Partition representing a districting plan
    :type partition: Partition

    :returns: :math:`L^2` norm of the Polsby-Popper scores
    :rtype: float
    """
    return math.sqrt(sum(value**2 for value in partition["polsby_popper"].values()))


def L_minus_1_polsby_popper(partition):
    """
    Returns the :math:`L^{-1}` norm of the Polsby-Popper scores
    for the given partition.

    :param partition: Partition representing a districting plan
    :type partition: Partition

    :returns: :math:`L^{-1}` norm of the Polsby-Popper scores
    :rtype: float
    """
    return len(partition.parts) / sum(
        1 / value for value in partition["polsby_popper"].values()
    )


no_worse_L_minus_1_polsby_popper = SelfConfiguringLowerBound(L_minus_1_polsby_popper)

no_worse_L1_reciprocal_polsby_popper = SelfConfiguringUpperBound(
    L1_reciprocal_polsby_popper
)
