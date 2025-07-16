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

    # frm: TODO:  Figure out what is going on with the "alias" parameter.
    #               It is used to get the value from the parent if there is
    #               a parent, but it is NOT used when computing the result
    #               for the first partition.  Seems like a logic bug...

    if partition.parent:
        return partition.parent[alias]
    else:
        result = {
          node
          for node in partition.graph.nodes
          # frm: original code:   if partition.graph.nodes[node]["boundary_node"]
          if partition.graph.node_data(node)["boundary_node"]
        }
        return result


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
        # frm: original code:   boundaries[part] += partition.graph.nodes[node]["boundary_perim"]
        boundaries[part] += partition.graph.node_data(node)["boundary_perim"]
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
        # frm: original code:   partition.graph.nodes[node]["boundary_perim"]
        partition.graph.node_data(node)["boundary_perim"]
        for node in inflow & graph_boundary
    )
    removed_perimeter = sum(
        # frm: original code:   partition.graph.nodes[node]["boundary_perim"]
        partition.graph.node_data(node)["boundary_perim"]
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

    # frm: RustworkX Note: 
    #
    #       The old NX code did not distinguish between edges and edge_ids - they were one 
    #       and the same.  However, in RX an edge is a tuple and an edge_id is an integer.
    #       The edges stored in partition["cut_edges_by_part"] are edges (tuples), so 
    #       we need to get the edge_id for each edge in order to access the data for the edge.
    
    # frm: Original Code:
    #    return {
    #        part: sum(
    #            partition.graph.edges[edge]["shared_perim"]
    #            for edge in partition["cut_edges_by_part"][part]
    #        )
    #    }
        
    # Get edge_ids for each edge (tuple)
    edge_ids_for_part = {
        part: [
            partition.graph.get_edge_id_from_edge(edge)
            for edge in partition["cut_edges_by_part"][part]
        ]
        for part in partition.parts
    }

    edge_to_edge_id_map = [
      (edge, partition.graph.get_edge_id_from_edge(edge)) 
      for edge in partition.graph.edges
    ]

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
        # frm: Original Code:   partition.graph.edges[edge]["shared_perim"] for edge in new_edges
        # frm: edges vs edge_ids:  edge_ids are wanted here (integers)
        partition.graph.edge_data(edge)["shared_perim"] for edge in new_edges
    )
    removed_perimeter = sum(
        # frm: Original Code:  partition.graph.edges[edge]["shared_perim"] for edge in old_edges
        # frm: edges vs edge_ids:  edge_ids are wanted here (integers)
        partition.graph.edge_data(edge)["shared_perim"] for edge in old_edges
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
    # frm: ???:  Does anyone ever use this?  It seems kind of useless...
    return partition.flips


def perimeter_of_part(partition, part: int) -> float:
    """
    Totals up the perimeter of the part in the partition.

    .. Warning::  frm: TODO:  Add code to enforce this warning...

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
