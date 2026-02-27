import math
from typing import Dict

# frm: TODO: Documentation: Add import of Partition just to be clear...


def compute_polsby_popper(area: float, perimeter: float) -> float:
    """
    Computes the Polsby-Popper score for a single district.

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


# Partition type hint left out due to circular import
# def polsby_popper(partition: Partition) -> Dict[int, float]:
def polsby_popper(partition) -> Dict[int, float]:
    """
    Computes Polsby-Popper compactness scores for each district in the partition.

    Args:
        partition (Partition): The partition to compute scores for

    Returns:
        Dict[int, float]: A dictionary mapping each district ID to its Polsby-Popper score
    """
    return {
        part: compute_polsby_popper(partition["area"][part], partition["perimeter"][part])
        for part in partition.parts
    }
