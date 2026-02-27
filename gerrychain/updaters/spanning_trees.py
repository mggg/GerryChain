"""
Updaters that compute spanning tree statistics.
"""

import math
from typing import Dict

import numpy


def _num_spanning_trees_in_district(partition, district: int) -> int:
    """Computes the number of spanning trees in a subgraph of the partition defined by a district.

    Args:
        partition (:class:`gerrychain.Partition`): :class:`gerrychain.Partition`
        district (int): A district label (part) in the partition.

    Returns:
        int: The number of spanning trees in the subgraph of the partition corresponding to
            district
    """
    laplacian = partition.graph.laplacian_matrix()
    L = numpy.delete(numpy.delete(laplacian.todense(), 0, 0), 1, 1)
    return math.exp(numpy.linalg.slogdet(L)[1])


def num_spanning_trees(partition) -> Dict[int, int]:
    """Return number of spanning trees in each part (district) of a partition.

    Returns:
        Dict[int, int]: The number of spanning trees in each part (district) of a partition.
    """
    return {part: _num_spanning_trees_in_district(partition, part) for part in partition.parts}
