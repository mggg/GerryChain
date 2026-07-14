"""
This module provides a set of functions to help determine and
manipulate the adjacency of geometries within a particular
graph. The functions in this module are used internally to ensure
that the geometry data that we are working with is sufficiently
well-defined to be used for analysis.

Some of the type hints in this module are intentionally left
unspecified because of import issues.
"""

import warnings
from collections.abc import Hashable, Iterable, Iterator
from typing import cast

from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

Adjacency = dict[Hashable, dict[Hashable, dict[str, float]]]


def neighbors(df: GeoDataFrame, adjacency: str) -> Adjacency:
    if adjacency not in ("rook", "queen"):
        raise ValueError(
            "The adjacency parameter provided is not supported. "
            'We support "queen" or "rook" adjacency.'
        )

    return adjacencies[adjacency](df.geometry)


def str_tree(geometries: GeoSeries) -> STRtree:
    """Creates a STR tree for spatial indexing. Useful for spatial operations.

    Args:
        geometries (GeoSeries): A Shapely geometry object to construct the tree
            from.

    Returns:
        STRtree: A Sort-Tile-Recursive tree for spatial indexing.
    """
    from shapely.strtree import STRtree

    try:
        tree = STRtree(geometries)
    except AttributeError:
        tree = STRtree(geometries)
    return tree


def neighboring_geometries(
    geometries: GeoSeries, tree: STRtree | None = None
) -> Iterator[tuple[Hashable, tuple[Hashable, ...]]]:
    """Generator yielding tuples of the form (id, (ids of neighbors)).

    Args:
        geometries (GeoSeries): A Shapeley geometry object to construct the
            tree from
        tree (STRtree | None, optional): A Sort-Tile-Recursive tree for spatial indexing.
            Defaults to None.

    Returns:
        Iterator[tuple[Hashable, tuple[Hashable, ...]]]: Geometry IDs and their neighboring IDs.
    """
    if tree is None:
        tree = str_tree(geometries)

    for geometry_id, geometry in geometries.items():
        geometry = cast(BaseGeometry, geometry)
        possible = tree.query(geometry)
        actual = tuple(
            cast(Hashable, geometries.index[p])
            for p in possible
            if (not geometries.iloc[p].is_empty) and geometries.index[p] != geometry_id
        )
        yield (geometry_id, actual)


def intersections_with_neighbors(
    geometries: GeoSeries,
) -> Iterator[tuple[Hashable, dict[Hashable, BaseGeometry]]]:
    """Generator yielding tuples of the form (id, {neighbor_id: intersection}).

    Note:
        The intersections may be empty!

    Args:
        geometries (GeoSeries): A Shapeley geometry object.

    Returns:
        Iterator[tuple[Hashable, dict[Hashable, BaseGeometry]]]: Geometry IDs mapped to their
            intersections with neighboring geometries.
    """
    for i, neighbors in neighboring_geometries(geometries):
        geometry = cast(BaseGeometry, geometries[i])
        intersections = {
            j: geometry.intersection(cast(BaseGeometry, geometries[j])) for j in neighbors
        }
        yield (i, intersections)


def warn_for_overlaps(
    intersection_pairs: Iterable[tuple[Hashable, dict[Hashable, BaseGeometry]]],
) -> Iterator[tuple[Hashable, dict[Hashable, BaseGeometry]]]:
    """Return A generator yielding tuples of intersection pairs.

    Args:
        intersection_pairs (Iterable[tuple[Hashable, dict[Hashable, BaseGeometry]]]): Geometry IDs
            mapped to their intersections with neighboring geometries.

    Returns:
        Iterator[tuple[Hashable, dict[Hashable, BaseGeometry]]]: The original intersection pairs.

    Raises:
        UserWarning: if there are overlaps among the given polygons
    """
    overlaps: set[frozenset[Hashable]] = set()
    for i, intersections in intersection_pairs:
        overlaps.update(
            set(
                frozenset((i, j))
                for j, intersection in intersections.items()
                if intersection.area > 0
            )
        )
        yield (i, intersections)
    if len(overlaps) > 0:
        warnings.warn(f"Found overlaps among the given polygons. Indices of overlaps: {overlaps}")


def queen(geometries: GeoSeries) -> Adjacency:
    """Return queen adjacency dictionary for the given collection of polygons.

    Args:
        geometries (GeoSeries): A Shapeley geometry object.

    Returns:
        Adjacency: The queen adjacency dictionary for the given collection of polygons.
    """
    intersection_pairs = warn_for_overlaps(intersections_with_neighbors(geometries))

    return {
        i: {
            j: {"shared_perim": intersection.length}
            for j, intersection in intersections.items()
            if (not intersection.is_empty)
        }
        for i, intersections in intersection_pairs
    }


def rook(geometries: GeoSeries) -> Adjacency:
    """Return rook adjacency dictionary for the given collection of polygons.

    Args:
        geometries (GeoSeries): A Shapeley geometry object.

    Returns:
        Adjacency: The rook adjacency dictionary for the given collection of polygons.
    """
    return {
        i: {j: data for j, data in neighbors.items() if data["shared_perim"] > 0}
        for i, neighbors in queen(geometries).items()
    }


# Dictionary mapping adjacency types to their corresponding functions.
adjacencies = {"rook": rook, "queen": queen}
