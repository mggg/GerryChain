import collections
import functools


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


def on_edge_flow(initializer, alias):
    """
    Use this decorator to create an updater that responds to flows of cut
    edges between parts of the partition.

    Decorate a function that takes:
    - The partition
    - The previous value of the updater for a fixed part P_i
    - The new cut edges that are just joining P_i at this step
    - The old cut edges that are just leaving P_i at this step
    and returns:
    - The new value of the updater for the fixed part P_i.

    This will create an updater whose values are dictionaries of the
    form `{part: <value of the given function on the part>}`.

    The initializer, by contrast, should take the entire partition and
    return the entire `{part: <value>}` dictionary.

    Example:

    .. code-block:: python

        @on_edge_flow(initializer, alias='my_updater')
        def my_updater(partition, previous, new_edges, old_edges):
            # return new value of the part
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(partition):
            if not partition.parent:
                return initializer(partition)
            new_by_part = put_edges_into_parts(new_cuts(partition), partition.assignment)
            obsolete_by_part = put_edges_into_parts(obsolete_cuts(partition),
                                                    partition.parent.assignment)
            previous = partition.parent[alias]
            return {part: f(partition, previous[part], new_edges=new_by_part[part],
                            old_edges=obsolete_by_part[part])
                    for part in partition.parts}
        return wrapper
    return decorator


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
