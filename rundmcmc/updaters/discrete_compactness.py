import math


def boundary_node_count_of_part(partition, part):
    """
    Counts the nodes on the boundary of a part.
    Requires that 'cut_edges' be an updater, and 'exterior_boundaries_as_a_set' be an updater.
    """

    # Counts the nodes that are on the edge of the (US) state
    state_boundary_count = len(partition['exterior_boundaries_as_a_Set'][part])

    # Counts the nodes of the part that share an edge with a different part.
    partition_boundary_count = len(set([x for y in partition['cut_edges_by_part'][part]
                                       for x in y]).intersection(partition.parts[part]))

    return state_boundary_count + partition_boundary_count


def boundary_node_counts(partition):
    return {part: boundary_node_count_of_part(partition, part) for part in partition.parts}


def node_counts(partition):
    return {part: len(partition.parts[part]) for part in partition.parts.keys()}


def compute_discrete_polsby_popper(discrete_area, discrete_perimeter):
    return 4 * math.pi * discrete_area / discrete_perimeter**2


def discrete_polsby_popper(partition):
    return {part: compute_discrete_polsby_popper(partition['node_counts'][part],
                                                 partition['boundary_node_counts'][part])
        for part in partition.parts}
