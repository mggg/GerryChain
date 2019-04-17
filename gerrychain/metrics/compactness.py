import math


def compute_polsby_popper(area, perimeter):
    try:
        return 4 * math.pi * area / perimeter ** 2
    except ZeroDivisionError:
        return math.nan


def polsby_popper(partition):
    return {
        part: compute_polsby_popper(
            partition["area"][part], partition["perimeter"][part]
        )
        for part in partition.parts
    }
