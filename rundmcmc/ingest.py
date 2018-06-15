import pysal as ps
import geopandas as gp
import pandas as pd
import numpy as np


def ingest(filepath, name_of_geoid_col, nbr_col_name=None, perim_col_name=None):
    """Generate (rook) neighbor and perimeter information from a shapefile or csv

    :filepath: Path to input shapefile or csv location.
    :name_of_geoid_col: name of column with unique identifier
    :nbr_col_name: column name (if csv adjacencyframe format) with adjacent neighbors
    :perim_col_name: column name (if csv adjacencyframe format) with shared perimeter

    :returns: Tuple (neighbors, perims, geoid_col) to be passed to
        :func:`.make_graph`. `neighbors` is a nested list of neighbors.
        `perims` is a nested list of perimeters. `geoid_col` is a list of the
        geoids of shapes.

    """

    if filepath.split(".")[-1] == "csv":
        df = pd.read_csv(filepath)
        if (nbr_col_name not in df.columns) or (perim_col_name not in df.columns):
            print("ERROR! Need a valid column name for neighbor and perimeter")

        uniques = df[name_of_geoid_col].unique().tolist()
        lookup = dict(zip(uniques, range(len(uniques))))

        neighbors = {lookup[x[0]]:[lookup[y] for y in x[1]]
                     for x in df.groupby([name_of_geoid_col])[nbr_col_name]}

        shared_perims = {lookup[x[0]]:[y for y in x[1]]
                     for x in df.groupby([name_of_geoid_col])[perim_col_name]}

        sorted_keys = sorted(neighbors)
        for i in neighbors.keys():
             shared_perims[i] = [shared_perims[i][j] for j in np.argsort(neighbors[i])]
             neighbors[i] = sorted(neighbors[i])

    elif filepath.split(".")[-1] == "shp":
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
