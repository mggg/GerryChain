import collections
import math

from .flows import on_flow
from .cut_edges import on_edge_flow


def compute_polsby_popper(area, perimeter):
    return 4 * math.pi * area / perimeter**2


def polsby_popper(partition):
    return {part: compute_polsby_popper(partition['areas'][part], partition['perimeters'][part])
            for part in partition.parts}


def boundary_nodes(partition, alias='boundary_nodes'):
    if partition.parent:
        return partition.parent[alias]
    return {node for node in partition.graph.nodes if partition.graph.nodes[node]['boundary_node']}


def initialize_exterior_boundaries_as_a_set(partition):
    part_boundaries = collections.defaultdict(set)
    for node in partition['boundary_nodes']:
        part_boundaries[partition.assignment[node]].add(node)
    return part_boundaries


@on_flow(initialize_exterior_boundaries_as_a_set, alias='exterior_boundaries_as_a_set')
def exterior_boundaries_as_a_set(partition, previous, inflow, outflow):
    graph_boundary = partition['boundary_nodes']
    return (previous | (inflow & graph_boundary)) - outflow


def initialize_exterior_boundaries(partition):
    graph_boundary = partition['boundary_nodes']
    return {part: sum(partition.graph.nodes[node]['boundary_perim']
                      for node in partition.parts[part] & graph_boundary)
                      for part in partition.parts}


@on_flow(initialize_exterior_boundaries, alias='exterior_boundaries')
def exterior_boundaries(partition, previous, inflow, outflow):
    graph_boundary = partition['boundary_nodes']
    added_perimeter = sum(partition.graph.nodes[node]['boundary_perim']
                          for node in inflow & graph_boundary)
    removed_perimeter = sum(partition.graph.nodes[node]['boundary_perim']
                            for node in outflow & graph_boundary)
    return previous + added_perimeter - removed_perimeter


def initialize_interior_boundaries(partition):
    return {part: sum(partition.graph.edges[edge]['shared_perim']
                      for edge in partition['cut_edges_by_part'][part])
            for part in partition.parts}


@on_edge_flow(initialize_interior_boundaries, alias='interior_boundaries')
def interior_boundaries(partition, previous, new_edges, old_edges):
    added_perimeter = sum(partition.graph.edges[edge]['shared_perim'] for edge in new_edges)
    removed_perimeter = sum(partition.graph.edges[edge]['shared_perim'] for edge in old_edges)
    return previous + added_perimeter - removed_perimeter


def flips(partition):
    return partition.flips


def perimeter_of_part(partition, part):
    """
    Totals up the perimeter of the part in the partition.
    Requires that 'boundary_perim' be a node attribute, 'shared_perim' be an edge
    attribute, 'cut_edges' be an updater, and 'exterior_boundaries' be an updater.
    """
    exterior_perimeter = partition['exterior_boundaries'][part]
    interior_perimeter = partition['interior_boundaries'][part]

    return exterior_perimeter + interior_perimeter


def perimeters(partition):
    return {part: perimeter_of_part(partition, part) for part in partition.parts}
