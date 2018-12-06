import warnings

from shapely.strtree import STRtree


def neighbors(df, adjacency):
    if adjacency not in ("rook", "queen"):
        raise ValueError(
            "The adjacency parameter provided is not supported. "
            'We support "queen" or "rook" adjacency.'
        )

    return adjacencies[adjacency](df.geometry)


def str_tree(geometries):
    """Add ids to geometries and create a STR tree for spatial indexing.
    Use this for all spatial operations!
    """
    for i in geometries.index:
        geometries[i].id = i
    try:
        tree = STRtree(geometries)
    except AttributeError:
        tree = STRtree(geometries)
    return tree


def neighboring_geometries(geometries, tree=None):
    """Generator yielding tuples of the form (id, (ids of neighbors)).
    """
    if tree is None:
        tree = str_tree(geometries)

    for geometry in geometries:
        possible = tree.query(geometry)
        actual = tuple(
            p.id for p in possible if (not p.is_empty) and p.id != geometry.id
        )
        yield (geometry.id, actual)


def intersections_with_neighbors(geometries):
    """Generator yielding tuples of the form (id, {neighbor_id: intersection}).
    The intersections may be empty!
    """
    for i, neighbors in neighboring_geometries(geometries):
        intersections = {
            j: geometries[i].intersection(geometries[j]) for j in neighbors
        }
        yield (i, intersections)


def warn_for_overlaps(intersection_pairs):
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
    """Return queen adjacency dictionary for the given collection of polygons."""
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
    """Return rook adjacency dictionary for the given collection of polygons."""
    return {
        i: {j: data for j, data in neighbors.items() if data["shared_perim"] > 0}
        for i, neighbors in queen(geometries).items()
    }


adjacencies = {"rook": rook, "queen": queen}
