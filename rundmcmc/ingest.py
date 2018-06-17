import pysal as ps
import geopandas as gp


def ingest(filepath, name_of_geoid_col):
    """Generate (rook) neighbor and perimeter information from a shapefile.

    :filepath: Path to input shapefile location.

    :returns: Tuple (neighbors, perims, geoid_col) to be passed to
        :func:`.make_graph`. `neighbors` is a nested list of neighbors.
        `perims` is a nested list of perimeters. `geoid_col` is a list of the
        geoids of shapes.

    """

    df = gp.read_file(filepath)

    # Generate rook neighbor lists from dataframe.
    neighbors = ps.weights.Rook.from_dataframe(df, geom_col="geometry").neighbors
    for n in neighbors:
        neighbors[n] = sorted(neighbors[n])

    shared_perims = {}
    for shape in neighbors:
        shared_perims[shape] = []

        for n in neighbors[shape]:
            shared_perims[shape].append(
                df.loc[shape, "geometry"].intersection(
                    df.loc[n, "geometry"])
                .length)

    sorted_keys = sorted(neighbors)

    return([neighbors[i] for i in sorted_keys],
           [shared_perims[i] for i in sorted_keys],
           [df.loc[i, name_of_geoid_col] for i in sorted_keys])


if __name__ == "__main__":
    ingest("testData/testData.shp", "CD")
