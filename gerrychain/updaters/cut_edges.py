import collections
from typing import Dict, List, Set, Tuple
from .flows import on_edge_flow, neighbor_flips



def _put_edges_into_parts(cut_edges: List, assignment: Dict) -> Dict:
    """
    :param cut_edges: A list of cut_edges in a graph which are to be separated
        into their respective parts within the partition according to
        the given assignment.
    :type cut_edges: List
    :param assignment: A dictionary mapping nodes to their respective
        parts within the partition.
    :type assignment: Dict

    :returns: A dictionary mapping each part of a partition to the set of cut_edges
        in that part.
    :rtype: Dict
    """
    by_part = collections.defaultdict(set)
    for edge in cut_edges:
        # add edge to the sets corresponding to the parts it touches
        by_part[assignment.mapping[edge[0]]].add(edge)
        by_part[assignment.mapping[edge[1]]].add(edge)
    return by_part

def _new_cuts(partition) -> Set[Tuple]:
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


def _obsolete_cuts(partition) -> Set[Tuple]:
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

def initialize_cut_edges(partition):
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    frm: TODO:  This description should be updated.  Cut_edges are edges that touch
                two different parts (districts).  They are the internal boundaries
                between parts (districts).  This routine finds all of the cut_edges
                in the graph and then creates a dict that stores all of the cut_edges
                for each part (district).  This dict becomes the value of 
                partition["cut_edges"].

                Peter agreed: 
                    Ah, you are correct. It maps parts to cut edges, not just any edges in the partition



    :returns: A dictionary mapping each part of a partition to the set of edges
        in that part.
    :rtype: Dict
    """
    # Compute the set of edges that are "cut_edges" - that is, edges that go from
    # one part (district) to another. 
    cut_edges = {
        tuple(sorted(edge))
        # frm: edges vs edge_ids:  edges are wanted here (tuples)
        for edge in partition.graph.edges
        if partition.crosses_parts(edge)
    }
    return _put_edges_into_parts(cut_edges, partition.assignment)


@on_edge_flow(initialize_cut_edges, alias="cut_edges_by_part")
def cut_edges_by_part(
    partition, previous: Set[Tuple], new_edges: Set[Tuple], old_edges: Set[Tuple]
) -> Set[Tuple]:
    #
    # frm TODO: Update / expand the documentation for this routine.
    # 
    # This only operates on cut-edges and not on all of the 
    # edges in a partition.  A "cut-edge" is an edge that spans two districts.
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
            for edge in partition.graph.edges
            if partition.crosses_parts(edge)
        }
    # Edges that weren't cut, but now are cut
    # We sort the tuples to make sure we don't accidentally end
    # up with both (4,5) and (5,4) (for example) in it
    new, obsolete = _new_cuts(partition), _obsolete_cuts(partition)

    return (parent["cut_edges"] | new) - obsolete
