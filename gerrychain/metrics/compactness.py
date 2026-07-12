from __future__ import annotations

import math
from collections.abc import Hashable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..partition.partition import Partition


def compute_polsby_popper(area: float, perimeter: float) -> float:
    """Computes the Polsby-Popper score for a single district.

    Args:
        area (float): The area of the district
        perimeter (float): The perimeter of the district

    Returns:
        float: The Polsby-Popper score for the district
    """
    try:
        return 4 * math.pi * area / perimeter**2
    except ZeroDivisionError:
        return math.nan


def polsby_popper(partition: Partition) -> dict[Hashable, float]:
    """Computes Polsby-Popper compactness scores for each district in the partition.

    This function computes Polsby-Popper compactness scores for each district in the partition. It
    returns a dictionary mapping each district ID to its Polsby-Popper score.

    Args:
        partition (Partition): The partition to compute scores for

    Returns:
        dict[Hashable, float]: A dictionary mapping each district ID to its Polsby-Popper score
    """
    return {
        part: compute_polsby_popper(partition["area"][part], partition["perimeter"][part])
        for part in partition.parts
    }
