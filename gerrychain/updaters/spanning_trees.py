"""Updaters that compute spanning tree statistics."""
import math
import numpy
import networkx


def _num_spanning_trees_in_district(partition, district):
    """Given a district ID, returns the number of spanning trees in the
    subgraph of self corresponding to the district.

    Uses Kirchoff's theorem to compute the number of spanning trees.

    :param partition: :class:`gerrychain.Partition`
    :param district: A district label (part) in the partition.
    :return: The number of spanning trees in the subgraph of the
    partition corresponding to district
    """
    graph = partition.subgraphs[district]
    laplacian = networkx.laplacian_matrix(graph)
    L = numpy.delete(numpy.delete(laplacian.todense(), 0, 0), 1, 1)
    return math.exp(numpy.linalg.slogdet(L)[1])


def num_spanning_trees(partition):
    """Returns the number of spanning trees in each part (district) of a partition."""
    return {
        part: _num_spanning_trees_in_district(partition, part)
        for part in partition.parts
    }
