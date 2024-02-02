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
from geopandas import GeoDataFrame
from typing import Dict


def neighbors(df: GeoDataFrame, adjacency: str) -> Dict:
    if adjacency not in ("rook", "queen"):
        raise ValueError(
            "The adjacency parameter provided is not supported. "
            'We support "queen" or "rook" adjacency.'
        )

    return adjacencies[adjacency](df.geometry)


def str_tree(geometries):
    """
    Add ids to geometries and create a STR tree for spatial indexing.
    Use this for all spatial operations!

    :param geometries: A Shapely geometry object to construct the tree from.
    :type geometries: shapely.geometry.BaseGeometry

    :returns: A Sort-Tile-Recursive tree for spatial indexing.
    :rtype: shapely.strtree.STRtree
    """
    from shapely.strtree import STRtree

    try:
        tree = STRtree(geometries)
    except AttributeError:
        tree = STRtree(geometries)
    return tree


def neighboring_geometries(geometries, tree=None):
    """
    Generator yielding tuples of the form (id, (ids of neighbors)).

    :param geometries: A Shapeley geometry object to construct the tree from
    :type geometries: shapely.geometry.BaseGeometry
    :param tree: A Sort-Tile-Recursive tree for spatial indexing. Default is None.
    :type tree: shapely.strtree.STRtree, optional

    :returns: A generator yielding tuples of the form (id, (ids of neighbors))
    :rtype: Generator
    """
    if tree is None:
        tree = str_tree(geometries)

    for geometry_id, geometry in geometries.items():
        possible = tree.query(geometry)
        actual = tuple(
            geometries.index[p]
            for p in possible
            if (not geometries.iloc[p].is_empty) and geometries.index[p] != geometry_id
        )
        yield (geometry_id, actual)


def intersections_with_neighbors(geometries):
    """
    Generator yielding tuples of the form (id, {neighbor_id: intersection}).
    The intersections may be empty!

    :param geometries: A Shapeley geometry object.
    :type geometries: shapely.geometry.BaseGeometry

    :returns: A generator yielding tuples of the form (id, {neighbor_id: intersection})
    :rtype: Generator
    """
    for i, neighbors in neighboring_geometries(geometries):
        intersections = {
            j: geometries[i].intersection(geometries[j]) for j in neighbors
        }
        yield (i, intersections)


def warn_for_overlaps(intersection_pairs):
    """
    :param intersection_pairs: An iterable of tuples of
        the form (id, {neighbor_id: intersection})
    :type intersection_pairs: Iterable

    :returns: A generator yielding tuples of intersection pairs
    :rtype: Generator

    :raises: UserWarning if there are overlaps among the given polygons
    """
    overlaps = set()
    for i, intersections in intersection_pairs:
        overlaps.update(
            set(
                tuple(sorted([i, j]))
                for j, intersection in intersections.items()
                if intersection.area > 0
            )
        )
        yield (i, intersections)
    if len(overlaps) > 0:
        warnings.warn(
            "Found overlaps among the given polygons. Indices of overlaps: {}".format(
                overlaps
            )
        )


def queen(geometries):
    """
    :param geometries: A Shapeley geometry object.
    :type geometries: shapely.geometry.BaseGeometry

    :returns: The queen adjacency dictionary for the given collection of polygons.
    :rtype: Dict
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


def rook(geometries):
    """
    :param geometries: A Shapeley geometry object.
    :type geometries: shapely.geometry.BaseGeometry

    :returns: The rook adjacency dictionary for the given collection of polygons.
    :rtype: Dict
    """
    return {
        i: {j: data for j, data in neighbors.items() if data["shared_perim"] > 0}
        for i, neighbors in queen(geometries).items()
    }


# Dictionary mapping adjacency types to their corresponding functions.
adjacencies = {"rook": rook, "queen": queen}
