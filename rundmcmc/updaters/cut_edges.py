import collections


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
            for neighbor in partition.graph[node]
            if partition.crosses_parts((node, neighbor))}


def obsolete_cuts(partition):
    """The edges that were cut, but now are not"""
    return {tuple(sorted((node, neighbor))) for node in partition.flips
            for neighbor in partition.graph.neighbors(node)
            if partition.parent.crosses_parts((node, neighbor)) and
            not partition.crosses_parts((node, neighbor))}


def cut_edges_by_part(partition, alias='cut_edges_by_part'):
    if not partition.parent:
        edges = {tuple(sorted(edge)) for edge in partition.graph.edges
                if partition.crosses_parts(edge)}
        return put_edges_into_parts(edges, partition.assignment)

    new_by_part = put_edges_into_parts(new_cuts(partition), partition.assignment)
    obsolete_by_part = put_edges_into_parts(obsolete_cuts(partition), partition.parent.assignment)

    new_cut_edges = collections.defaultdict(set)
    previous_value = partition.parent[alias]
    for part in partition.parts:
        new_cut_edges[part] = (previous_value[part] | new_by_part[part]) - obsolete_by_part[part]
    return new_cut_edges


def cut_edges(partition):
    parent = partition.parent

    if not parent:
        return {edge for edge in partition.graph.edges
                if partition.crosses_parts(edge)}
    # Edges that weren't cut, but now are cut
    # We sort the tuples to make sure we don't accidentally end
    # up with both (4,5) and (5,4) (for example) in it
    new, obsolete = new_cuts(partition), obsolete_cuts(partition)

    return (parent['cut_edges'] | new) - obsolete
