import collections
from typing import Dict, List, Set, Tuple
from .flows import on_edge_flow, neighbor_flips


# frm ???:  Is this intended to be externally visible / useful?

def put_edges_into_parts(edges: List, assignment: Dict) -> Dict:
    """
    :param edges: A list of edges in a graph which are to be separated
        into their respective parts within the partition according to
        the given assignment.
    :type edges: List
    :param assignment: A dictionary mapping nodes to their respective
        parts within the partition.
    :type assignment: Dict

    :returns: A dictionary mapping each part of a partition to the set of edges
        in that part.
    :rtype: Dict
    """
    by_part = collections.defaultdict(set)
    for edge in edges:
        # add edge to the sets corresponding to the parts it touches
        by_part[assignment.mapping[edge[0]]].add(edge)
        by_part[assignment.mapping[edge[1]]].add(edge)
    return by_part


# frm ???:  Is this intended to be externally visible / useful?

def new_cuts(partition) -> Set[Tuple]:
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: The set of edges that were not cut, but now are.
    :rtype: Set[Tuple]
    """
    return {
        (node, neighbor)
        for node, neighbor in neighbor_flips(partition)
        if partition.crosses_parts((node, neighbor))
    }


# frm ???:  Is this intended to be externally visible / useful?

def obsolete_cuts(partition) -> Set[Tuple]:
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: The set of edges that were cut, but now are not.
    :rtype: Set[Tuple]
    """
    return {
        (node, neighbor)
        for node, neighbor in neighbor_flips(partition)
        if partition.parent.crosses_parts((node, neighbor))
        and not partition.crosses_parts((node, neighbor))
    }


# frm ???:  Is this intended to be externally visible / useful?

def initialize_cut_edges(partition):
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: A dictionary mapping each part of a partition to the set of edges
        in that part.
    :rtype: Dict
    """
    # frm ???:  What does this do and why?
    #
    #           the if partition.crosses_parts(edge) is true if the edge
    #           is one that starts in one district/part and ends in another
    #           according to the given assignment.
    #           
    #           However, I am not sure what the tuple(sorted(edge)) does...
    #
    #               update: the tuple(sorted(edge)) just makes sure that
    #               the edge always has the smaller node_id first.
    #
    #           Note that I would lobby for the names "part" and "parts" to be
    #           changed to be "district" and "districts" just to avoid confusion
    #           with "partition" - parts of partitions warps my mind, and this 
    #           is all about re-DISTRICTing isn't it???
    #
    #           I would also lobby to have "crosses_parts" changed to "crosses_districts"
    #
    edges = {
        tuple(sorted(edge))
        # frm: edges vs edge_ids:  edges are wanted here (tuples)
        for edge in partition.graph.edges
        if partition.crosses_parts(edge)
    }
    return put_edges_into_parts(edges, partition.assignment)


@on_edge_flow(initialize_cut_edges, alias="cut_edges_by_part")
def cut_edges_by_part(
    partition, previous: Set[Tuple], new_edges: Set[Tuple], old_edges: Set[Tuple]
) -> Set[Tuple]:
    #
    # frm ???:  I think that this only operates on cut-edges and not on all of the 
    #           edges in a partition.  A "cut-edge" is an edge that spans two districts.
    #
    """
    Updater function that responds to the flow of edges between different partitions.

    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`
    :param previous: The previous set of edges for a fixed part of the given partition.
    :type previous: Set[Tuple]
    :param new_edges: The set of edges that have flowed into the given part of the
        partition.
    :type new_edges: Set[Tuple]
    :param old_edges: The set of cut edges in the previous partition.
    :type old_edges: Set[Tuple]

    :returns: The new set of cut edges for the newly generated partition.
    :rtype: Set
    """
    return (previous | new_edges) - old_edges


def cut_edges(partition):
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: The set of edges that are cut by the given partition.
    :rtype: Set[Tuple]
    """
    parent = partition.parent

    if not parent:
        return {
            tuple(sorted(edge))
            # frm: edges vs edge_ids:  edges are wanted here (tuples)
            for edge in partition.graph.edges
            if partition.crosses_parts(edge)
        }
    # Edges that weren't cut, but now are cut
    # We sort the tuples to make sure we don't accidentally end
    # up with both (4,5) and (5,4) (for example) in it
    new, obsolete = new_cuts(partition), obsolete_cuts(partition)

    return (parent["cut_edges"] | new) - obsolete
