from shapely.strtree import STRtree


def neighbors(df, adjacency):
    if adjacency not in ("rook", "queen"):
        raise ValueError(
            "The adjacency parameter provided is not supported. "
            'We support "queen" or "rook" adjacency.'
        )

    return adjacencies[adjacency](df.geometry)


def neighboring_geometries(geometries):
    for i in geometries.index:
        geometries[i].id = i

    try:
        tree = STRtree(geometries)
    except AttributeError:
        tree = STRtree(geometries)

    def get_neighbors(geometry):
        possible = tree.query(geometry)
        actual = [p for p in possible if (not p.is_empty) and p.id != geometry.id]
        return actual

    return geometries.apply(get_neighbors)


def queen(geometries):
    neighbors = neighboring_geometries(geometries)
    return {
        i: {
            neighbor.id: {"shared_perim": geometries[i].intersection(neighbor).length}
            for neighbor in neighbors[i]
        }
        for i in geometries.index
    }


def rook(geometries):
    return {
        i: {j: data for j, data in neighbors.items() if data["shared_perim"] > 0}
        for i, neighbors in queen(geometries).items()
    }


adjacencies = {"rook": rook, "queen": queen}
