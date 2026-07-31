from __future__ import annotations

import collections
from collections.abc import Hashable, Iterable
from typing import TYPE_CHECKING

from .._deprecated import deprecated_alias
from .flows import neighbor_flips, on_edge_flow

if TYPE_CHECKING:
    from ..partition.assignment import Assignment
    from ..partition.partition import Partition


def _put_edges_into_parts(
    cut_edges: Iterable[tuple[int, int]], assignment: Assignment
) -> dict[Hashable, set[tuple[int, int]]]:
    """Return A dictionary mapping each part of a partition to the set of cut_edges in that part.

    Args:
        cut_edges (list): A list of cut_edges in a graph which are to be separated into their
            respective parts within the partition according to the given assignment.
        assignment (dict): A dictionary mapping nodes to their respective parts within the
            partition.

    Returns:
        dict: A dictionary mapping each part of a partition to the set of cut_edges in that part.
    """
    by_part: collections.defaultdict[Hashable, set[tuple[int, int]]] = collections.defaultdict(set)
    for edge in cut_edges:
        # add edge to the sets corresponding to the parts it touches
        by_part[assignment.mapping[edge[0]]].add(edge)
        by_part[assignment.mapping[edge[1]]].add(edge)
    return by_part


def _new_cuts(partition: Partition) -> set[tuple[int, int]]:
    """Return set of edges that were not cut, but now are.

    Args:
        partition (Partition): A partition of a Graph

    Returns:
        set[tuple]: The set of edges that were not cut, but now are.
    """
    return {
        (node, neighbor)
        for node, neighbor in neighbor_flips(partition)
        if partition.crosses_parts((node, neighbor))
    }


def _obsolete_cuts(partition: Partition) -> set[tuple[int, int]]:
    """Return set of edges that were cut, but now are not.

    Args:
        partition (Partition): A partition of a Graph

    Returns:
        set[tuple]: The set of edges that were cut, but now are not.
    """
    assert partition.parent is not None
    return {
        (node, neighbor)
        for node, neighbor in neighbor_flips(partition)
        if partition.parent.crosses_parts((node, neighbor))
        and not partition.crosses_parts((node, neighbor))
    }


def initialize_cut_edges(partition: Partition) -> dict[Hashable, set[tuple[int, int]]]:
    """A dictionary mapping each part of a partition to the set of cut edges in that part.

    Args:
        partition (Partition): A partition of a Graph

    Returns:
        dict: A dictionary mapping each part of a partition to the set of cut edges in that part.
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
    partition: Partition,
    previous: set[tuple[int, int]],
    new_edges: set[tuple[int, int]],
    old_edges: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    #
    # frm TODO: Documentation: Update / expand the documentation for this routine.
    #
    # This only operates on cut-edges and not on all of the
    # edges in a partition.  A "cut-edge" is an edge that spans two districts.
    #
    """Updater that returns a dictionary mapping each part of a partition to the set of cut edges
    in that part.

    Args:
        partition (Partition): A partition of a Graph
        previous (set[tuple]): The previous set of edges for a fixed part of the given partition.
        new_edges (set[tuple]): The set of edges that have flowed into the given part of the
            partition.
        old_edges (set[tuple]): The set of cut edges in the previous partition.

    Returns:
        set: The new set of cut edges for the newly generated partition.
    """
    return (previous | new_edges) - old_edges


def cut_edges(partition: Partition) -> set[tuple[int, int]]:
    """Computes the set of edges for a given partition.

    Args:
        partition (Partition): A partition of a Graph

    Returns:
        set[tuple]: The set of edges that are cut by the given partition.
    """
    parent = partition.parent

    if not parent:
        return {
            tuple(sorted(edge)) for edge in partition.graph.edges if partition.crosses_parts(edge)
        }
    # Edges that weren't cut, but now are cut
    # We sort the tuples to make sure we don't accidentally end
    # up with both (4,5) and (5,4) (for example) in it
    new, obsolete = _new_cuts(partition), _obsolete_cuts(partition)

    return (parent["cut_edges"] | new) - obsolete


put_edges_into_parts = deprecated_alias(
    "gerrychain.updaters.cut_edges.put_edges_into_parts",
    "_put_edges_into_parts",
    _put_edges_into_parts,
)
new_cuts = deprecated_alias(
    "gerrychain.updaters.cut_edges.new_cuts",
    "_new_cuts",
    _new_cuts,
)
obsolete_cuts = deprecated_alias(
    "gerrychain.updaters.cut_edges.obsolete_cuts",
    "_obsolete_cuts",
    _obsolete_cuts,
)
