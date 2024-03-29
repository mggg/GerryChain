import collections

from .flows import on_flow
from .cut_edges import on_edge_flow
from typing import Dict, Set


def boundary_nodes(partition, alias: str = "boundary_nodes") -> Set:
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`
    :param alias: The name of the attribute that the boundary nodes are
        stored under. Default is 'boundary_nodes'.
    :type alias: str, optional

    :returns: The set of nodes in the partition that are on the boundary.
    :rtype: Set
    """
    if partition.parent:
        return partition.parent[alias]
    return {
        node
        for node in partition.graph.nodes
        if partition.graph.nodes[node]["boundary_node"]
    }


def initialize_exterior_boundaries_as_a_set(partition) -> Dict[int, Set]:
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: A dictionary mapping each part of a partition to the set of nodes
        in that part that are on the boundary.
    :rtype: Dict[int, Set]
    """
    part_boundaries = collections.defaultdict(set)
    for node in partition["boundary_nodes"]:
        part_boundaries[partition.assignment.mapping[node]].add(node)
    return part_boundaries


@on_flow(initialize_exterior_boundaries_as_a_set, alias="exterior_boundaries_as_a_set")
def exterior_boundaries_as_a_set(
    partition, previous: Set, inflow: Set, outflow: Set
) -> Set:
    """
    Updater function that responds to the flow of nodes between different partitions.

    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`
    :param previous: The previous set of exterior boundary nodes for a
        fixed part of the given partition.
    :type previous: Set
    :param inflow: The set of nodes that have flowed into the given part of the
        partition.
    :type inflow: Set
    :param outflow: The set of nodes that have flowed out of the given part of the
        partition.
    :type outflow: Set

    :returns: The new set of exterior boundary nodes for the given part of the
        partition.
    :rtype: Set
    """
    graph_boundary = partition["boundary_nodes"]
    return (previous | (inflow & graph_boundary)) - outflow


def initialize_exterior_boundaries(partition) -> Dict[int, float]:
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: A dictionary mapping each part of a partition to the total
        perimeter of the boundary nodes in that part.
    :rtype: Dict[int, float]
    """
    graph_boundary = partition["boundary_nodes"]
    boundaries = collections.defaultdict(lambda: 0)
    for node in graph_boundary:
        part = partition.assignment.mapping[node]
        boundaries[part] += partition.graph.nodes[node]["boundary_perim"]
    return boundaries


@on_flow(initialize_exterior_boundaries, alias="exterior_boundaries")
def exterior_boundaries(partition, previous: Set, inflow: Set, outflow: Set) -> Dict:
    """
    Updater function that responds to the flow of nodes between different partitions.

    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`
    :param previous: The previous set of exterior boundary nodes for a
        fixed part of the given partition.
    :type previous: Set
    :param inflow: The set of nodes that have flowed into the given part of the
        partition.
    :type inflow: Set
    :param outflow: The set of nodes that have flowed out of the given part of the
        partition.
    :type outflow: Set

    :returns: A dict mapping each part of the partition to the new exterior
        boundary of that part.
    :rtype: Dict
    """
    graph_boundary = partition["boundary_nodes"]
    added_perimeter = sum(
        partition.graph.nodes[node]["boundary_perim"]
        for node in inflow & graph_boundary
    )
    removed_perimeter = sum(
        partition.graph.nodes[node]["boundary_perim"]
        for node in outflow & graph_boundary
    )
    return previous + added_perimeter - removed_perimeter


def initialize_interior_boundaries(partition):
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: A dictionary mapping each part of a partition to the total
        perimeter the given part shares with other parts.
    :rtype: Dict[int, float]
    """
    return {
        part: sum(
            partition.graph.edges[edge]["shared_perim"]
            for edge in partition["cut_edges_by_part"][part]
        )
        for part in partition.parts
    }


@on_edge_flow(initialize_interior_boundaries, alias="interior_boundaries")
def interior_boundaries(
    partition, previous: Set, new_edges: Set, old_edges: Set
) -> Dict:
    """
    Updater function that responds to the flow of nodes between different partitions.

    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`
    :param previous: The previous set of exterior boundary nodes for a
        fixed part of the given partition.
    :type previous: Set
    :param new_edges: The set of edges that have flowed into the given part of the
        partition.
    :type new_edges: Set
    :param old_edges: The set of edges that have flowed out of the given part of the
        partition.
    :type old_edges: Set


    :returns: A dict mapping each part of the partition to the new interior
        boundary of that part.
    :rtype: Dict
    """
    added_perimeter = sum(
        partition.graph.edges[edge]["shared_perim"] for edge in new_edges
    )
    removed_perimeter = sum(
        partition.graph.edges[edge]["shared_perim"] for edge in old_edges
    )
    return previous + added_perimeter - removed_perimeter


def flips(partition) -> Dict:
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: The flips that were made to get from the parent partition to the
        given partition.
    :rtype: Dict
    """
    return partition.flips


def perimeter_of_part(partition, part: int) -> float:
    """
    Totals up the perimeter of the part in the partition.

    .. Warning::

        Requires that 'boundary_perim' be a node attribute, 'shared_perim' be an edge
        attribute, 'cut_edges' be an updater, and 'exterior_boundaries' be an updater.

    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`
    :param part: The id of the part of the partition whose perimeter we want to compute.
    :type part: int

    :returns: The perimeter of the desired part.
    :rtype: float
    """
    exterior_perimeter = partition["exterior_boundaries"][part]
    interior_perimeter = partition["interior_boundaries"][part]

    return exterior_perimeter + interior_perimeter


def perimeter(partition) -> Dict[int, float]:
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: A dictionary mapping each part of a partition to its perimeter.
    :rtype: Dict[int, float]
    """
    return {part: perimeter_of_part(partition, part) for part in partition.parts}
