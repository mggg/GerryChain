import math


def compute_polsby_popper(area, perimeter):
    try:
        return 4 * math.pi * area / perimeter ** 2
    except ZeroDivisionError:
        return math.nan


def polsby_popper(partition):
    """Computes Polsby-Popper compactness scores for each district in the partition.
    """
    return {
        part: compute_polsby_popper(
            partition["area"][part], partition["perimeter"][part]
        )
        for part in partition.parts
    }


def compute_schwartzberg(area, perimeter):
    try:
        return 2 * math.pi * math.sqrt(area / math.pi) / perimeter
    except ZeroDivisionError:
        return math.nan


def schwartzberg(partition):
    """Computes Schwartzberg compactness scores for each district in the partition.
    """
    return {
        part: compute_schwartzberg(
            partition["area"][part], partition["perimeter"][part]
        )
        for part in partition.parts
    }
