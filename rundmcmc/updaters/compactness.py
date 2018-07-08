import collections
import math

from .flows import on_flow


def compute_polsby_popper(area, perimeter):
    return 4 * math.pi * area / perimeter**2


def polsby_popper_updater(partition):
    return {part: compute_polsby_popper(partition['areas'][part], partition['perimeters'][part])
            for part in partition.parts}


def boundary_nodes(partition, alias='boundary_nodes'):
    if partition.parent:
        return partition.parent[alias]
    return {node for node in partition.graph.nodes if partition.graph.nodes[node]['boundary_node']}


def initialize_exterior_boundaries(partition):
    part_boundaries = collections.defaultdict(set)
    for node in partition['boundary_nodes']:
        part_boundaries[partition.assignment[node]].add(node)
    return part_boundaries


@on_flow(initialize_exterior_boundaries, alias='exterior_boundaries')
def exterior_boundaries(partition, previous, inflow, outflow):
    graph_boundary = partition['boundary_nodes']
    return (previous | (inflow & graph_boundary)) - outflow


def flips(partition):
    return partition.flips


def perimeter_of_part(partition, part):
    """
    Totals up the perimeter of the part in the partition.
    Requires that 'boundary_perim' be a node attribute, 'shared_perim' be an edge
    attribute, 'cut_edges' be an updater, and 'exterior_boundaries' be an updater.
    """
    exterior_perimeter = sum(partition.graph.nodes[node]['boundary_perim']
                             for node in partition['exterior_boundaries'][part])
    inter_part_perimeter = sum(partition.graph.edges[edge]['shared_perim']
                               for edge in partition['cut_edges_by_part'][part])
    return exterior_perimeter + inter_part_perimeter


def perimeters(partition):
    return {part: perimeter_of_part(partition, part) for part in partition.parts}
