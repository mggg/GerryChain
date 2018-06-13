import pysal as ps
import geopandas as gp


def ingest(filepath, name_of_geoid_col):
    """
        Reads in a shapefile through PySAL, and generates an
        adjacency list (rook adjacency). Then, compute shared
        perimeters for all adjacent shapes.

        :filepath: Filepath to input shapefile location.
    """
    df = gp.read_file(filepath)

    # Generate rook neighbor lists from dataframe.
    neighbors = ps.weights.Rook.from_dataframe(df, geom_col="geometry").neighbors
    for n in neighbors:
        neighbors[n] = sorted(neighbors[n])

    shared_perims = {}
    for shape in neighbors.keys():
        shared_perims[shape] = []

        for n in neighbors[shape]:
            shared_perims[shape].append(
                df.loc[shape, 'geometry'].intersection(
                    df.loc[n, 'geometry']).length)

    sorted_keys = sorted(neighbors)

    return ([neighbors[i] for i in sorted_keys],
            [shared_perims[i] for i in sorted_keys],
            [df.loc[i, name_of_geoid_col] for i in sorted_keys])


if __name__ == "__main__":
    ingest("testData/testData.shp", "CD")
