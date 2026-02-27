import collections
from typing import Dict, Set

from .cut_edges import on_edge_flow
from .flows import on_flow


def boundary_nodes(partition, alias: str = "boundary_nodes") -> Set:
    """Return set of nodes in the partition that are on the boundary.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph
        alias (str, optional): The name of the attribute that the boundary nodes are stored under.
            Default is 'boundary_nodes'.

    Returns:
        Set: The set of nodes in the partition that are on the boundary.
    """

    # Note that the "alias" parameter is used as the attribute name
    # on the partition - using this "alias" you can retrieve the
    # the data stored by an updater that uses this routine...

    if partition.parent:
        return partition.parent[alias]
    else:
        result = {
            node_id
            for node_id in partition.graph.node_indices
            if partition.graph.node_data(node_id)["boundary_node"]
        }
        return result


def initialize_exterior_boundaries_as_a_set(partition) -> Dict[int, Set]:
    """Return exterior boundary nodes for each part in the partition.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph

    Returns:
        Dict[int, Set]: A dictionary mapping each part of a partition to the set of nodes in that
            part that are on the boundary.
    """
    part_boundaries = collections.defaultdict(set)
    for node in partition["boundary_nodes"]:
        part_boundaries[partition.assignment.mapping[node]].add(node)

    return part_boundaries


@on_flow(initialize_exterior_boundaries_as_a_set, alias="exterior_boundaries_as_a_set")
def exterior_boundaries_as_a_set(partition, previous: Set, inflow: Set, outflow: Set) -> Set:
    """Updater function that responds to the flow of nodes between different partitions.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph
        previous (Set): The previous set of exterior boundary nodes for a fixed part of the given
            partition.
        inflow (Set): The set of nodes that have flowed into the given part of the partition.
        outflow (Set): The set of nodes that have flowed out of the given part of the partition.

    Returns:
        Set: The new set of exterior boundary nodes for the given part of the partition.
    """
    # Compute the new set of boundary nodes for the partition.
    #
    # The term, (inflow & graph_boundary), computes new nodes that are boundary nodes.
    #
    # the term, (previous | (inflow & graph_boundary)), adds those new boundary nodes to the
    # set of previous boundary nodes.
    #
    # Then all you need to do is subtract all of the nodes in the outflow to remove any of those
    # that happen to be boundary nodes...

    graph_boundary = partition["boundary_nodes"]
    return (previous | (inflow & graph_boundary)) - outflow


def initialize_exterior_boundaries(partition) -> Dict[int, float]:
    """Return A dictionary mapping each part of a partition to the total perimeter of the boundary.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph

    Returns:
        Dict[int, float]: A dictionary mapping each part of a partition to the total perimeter of
            the boundary nodes in that part.
    """
    graph_boundary = partition["boundary_nodes"]
    boundaries = collections.defaultdict(lambda: 0)
    for node in graph_boundary:
        part = partition.assignment.mapping[node]
        boundaries[part] += partition.graph.node_data(node)["boundary_perim"]
    return boundaries


@on_flow(initialize_exterior_boundaries, alias="exterior_boundaries")
def exterior_boundaries(partition, previous: Set, inflow: Set, outflow: Set) -> Dict:
    """Computes the total perimeter of the boundary nodes in each part of the partition.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph
        previous (Set): The previous set of exterior boundary nodes for a fixed part of the given
            partition.
        inflow (Set): The set of nodes that have flowed into the given part of the partition.
        outflow (Set): The set of nodes that have flowed out of the given part of the partition.

    Returns:
        Dict: A dict mapping each part of the partition to the new exterior boundary of that part.
    """
    graph_boundary = partition["boundary_nodes"]
    added_perimeter = sum(
        partition.graph.node_data(node)["boundary_perim"] for node in inflow & graph_boundary
    )
    removed_perimeter = sum(
        partition.graph.node_data(node)["boundary_perim"] for node in outflow & graph_boundary
    )
    return previous + added_perimeter - removed_perimeter


def initialize_interior_boundaries(partition):
    """Return A dictionary mapping each part of a partition to the total perimeter the given part.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph

    Returns:
        Dict[int, float]: A dictionary mapping each part of a partition to the total perimeter the
            given part shares with other parts.
    """

    # RustworkX Note:
    #
    # The old NX code did not distinguish between edges and edge_ids - they were one
    # and the same.  However, in RX an edge is a tuple and an edge_id is an integer.
    # The edges stored in partition["cut_edges_by_part"] are edges (tuples), so
    # we need to get the edge_id for each edge in order to access the data for the edge.

    # Get edge_ids for each edge (tuple)
    edge_ids_for_part = {
        part: [
            partition.graph.get_edge_id_from_edge(edge)
            for edge in partition["cut_edges_by_part"][part]
        ]
        for part in partition.parts
    }

    # Compute length of the shared perimeter of each part
    shared_perimeters_for_part = {
        part: sum(
            partition.graph.edge_data(edge_id)["shared_perim"]
            for edge_id in edge_ids_for_part[part]
        )
        for part in partition.parts
    }

    return shared_perimeters_for_part


@on_edge_flow(initialize_interior_boundaries, alias="interior_boundaries")
def interior_boundaries(partition, previous: Set, new_edges: Set, old_edges: Set) -> Dict:
    """Computes the total perimeter of the shared boundary between different parts of the partition.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph
        previous (Set): The previous set of exterior boundary nodes for a fixed part of the given
            partition.
        new_edges (Set): The set of edges that have flowed into the given part of the partition.
        old_edges (Set): The set of edges that have flowed out of the given part of the partition.

    Returns:
        Dict: A dict mapping each part of the partition to the new interior boundary of that part.
    """

    added_perimeter = sum(
        partition.graph.edge_data(partition.graph.get_edge_id_from_edge(edge))["shared_perim"]
        for edge in new_edges
    )
    removed_perimeter = sum(
        partition.graph.edge_data(partition.graph.get_edge_id_from_edge(edge))["shared_perim"]
        for edge in old_edges
    )
    return previous + added_perimeter - removed_perimeter


def flips(partition) -> Dict:
    """Return flips that were made to get from the parent partition to the given partition.

    This function returns flips that were made to get from the parent partition to the given
    partition. It returns flips that were made to get from the parent partition to the given
    partition.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph

    Returns:
        Dict: The flips that were made to get from the parent partition to the given partition.
    """
    # frm: ???:  Does anyone ever use this?  It seems kind of useless...
    return partition.flips


def perimeter_of_part(partition, part: int) -> float:
    """Totals up the perimeter of the part in the partition.

    .. Warning::

        Requires that 'boundary_perim' be a node attribute, 'shared_perim' be an edge attribute,
        'cut_edges' be an updater, and 'exterior_boundaries' be an updater.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph
        part (int): The id of the part of the partition whose perimeter we want to compute.

    Returns:
        float: The perimeter of the desired part.
    """

    # frm: TODO: Refactoring:   Add code to enforce the warning in the docstring above

    exterior_perimeter = partition["exterior_boundaries"][part]
    interior_perimeter = partition["interior_boundaries"][part]

    return exterior_perimeter + interior_perimeter


def perimeter(partition) -> Dict[int, float]:
    """Computes the perimeter of each part in the partition.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): A partition of a Graph

    Returns:
        Dict[int, float]: A dictionary mapping each part of a partition to its perimeter.
    """
    return {part: perimeter_of_part(partition, part) for part in partition.parts}
