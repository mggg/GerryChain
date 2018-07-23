import collections

from .flows import on_edge_flow


def put_edges_into_parts(edges, assignment):
    by_part = collections.defaultdict(set)
    for edge in edges:
        # add edge to the sets corresponding to the parts it touches
        by_part[assignment[edge[0]]].add(edge)
        by_part[assignment[edge[1]]].add(edge)
    return by_part


def new_cuts(partition):
    """The edges that were not cut, but now are"""
    return {tuple(sorted((node, neighbor))) for node in partition.flips
            for neighbor in partition.graph.neighbors(node)
            if partition.crosses_parts((node, neighbor))}


def obsolete_cuts(partition):
    """The edges that were cut, but now are not"""
    return {tuple(sorted((node, neighbor))) for node in partition.flips
            for neighbor in partition.graph.neighbors(node)
            if partition.parent.crosses_parts((node, neighbor)) and
            not partition.crosses_parts((node, neighbor))}


def initialize_cut_edges(partition):
    edges = {tuple(sorted(edge)) for edge in partition.graph.edges
             if partition.crosses_parts(edge)}
    return put_edges_into_parts(edges, partition.assignment)


@on_edge_flow(initialize_cut_edges, alias='cut_edges_by_part')
def cut_edges_by_part(partition, previous, new_edges, old_edges):
    return (previous | new_edges) - old_edges


def cut_edges(partition):
    parent = partition.parent

    if not parent:
        return {tuple(sorted(edge)) for edge in partition.graph.edges
                if partition.crosses_parts(edge)}
    # Edges that weren't cut, but now are cut
    # We sort the tuples to make sure we don't accidentally end
    # up with both (4,5) and (5,4) (for example) in it
    new, obsolete = new_cuts(partition), obsolete_cuts(partition)

    return (parent['cut_edges'] | new) - obsolete
