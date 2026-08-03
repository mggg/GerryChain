"""
Updaters that compute spanning tree statistics.
"""

from __future__ import annotations

import math
from collections.abc import Hashable
from typing import TYPE_CHECKING

import numpy

if TYPE_CHECKING:
    from ..partition.partition import Partition


def _num_spanning_trees_in_district(partition: Partition, district: Hashable) -> int:
    """Computes the number of spanning trees in a subgraph of the partition defined by a district.

    Args:
        partition (Partition): Partition
        district (Hashable): A district label (part) in the partition.

    Returns:
        int: The number of spanning trees in the subgraph of the partition corresponding to
            district
    """
    laplacian = partition.graph.laplacian_matrix()
    L = numpy.delete(numpy.delete(laplacian.todense(), 0, 0), 1, 1)
    return round(math.exp(numpy.linalg.slogdet(L)[1]))


def num_spanning_trees(partition: Partition) -> dict[Hashable, int]:
    """Return number of spanning trees in each part (district) of a partition.

    Returns:
        dict[Hashable, int]: The number of spanning trees in each part of a partition.
    """
    return {part: _num_spanning_trees_in_district(partition, part) for part in partition.parts}
