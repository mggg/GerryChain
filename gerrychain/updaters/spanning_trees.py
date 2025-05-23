"""
Updaters that compute spanning tree statistics.
"""

import math
import numpy
# frm TODO: Remove dependency on NetworkX
#           The only dependency is for the laplacian_matrix function:
#               laplacian = networkx.laplacian_matrix(graph)
import networkx
from typing import Dict


def _num_spanning_trees_in_district(partition, district: int) -> int:
    """
    Given a district ID, returns the number of spanning trees in the
    subgraph of self corresponding to the district.

    Uses Kirchoff's theorem to compute the number of spanning trees.

    :param partition: :class:`gerrychain.Partition`
    :type partition: :class:`gerrychain.Partition`
    :param district: A district label (part) in the partition.
    :type district: int

    :returns: The number of spanning trees in the subgraph of the
        partition corresponding to district
    :rtype: int
    """
    graph = partition.subgraphs[district]
    # frm: TODO:  Replace with Graph.laplacian_matrix() for RX compatibility...
    laplacian = networkx.laplacian_matrix(graph)
    L = numpy.delete(numpy.delete(laplacian.todense(), 0, 0), 1, 1)
    return math.exp(numpy.linalg.slogdet(L)[1])


def num_spanning_trees(partition) -> Dict[int, int]:
    """
    :returns: The number of spanning trees in each part (district) of a partition.
    :rtype: Dict[int, int]
    """
    return {
        part: _num_spanning_trees_in_district(partition, part)
        for part in partition.parts
    }
