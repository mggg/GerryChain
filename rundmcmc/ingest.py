
import pysal as ps
import geopandas as gp


def ingest(filepath, name_of_geoid_col):
    """
        Reads in a shapefile through PySAL, and generates an
        adjacency matrix (rook adjacency). Then, load the converted
        NumPy data from PySAL into NetworkX.

        :filepath: Filepath to input shapefile location.
    """
    df = gp.read_file(filepath)

    # Iterate over rows from dataframe and assign perimeters.
    for i, _ in df.iterrows():
        poly = df.loc[i, "geometry"]
        df.loc[i, "perimeter"] = poly.length

    # Generate rook neighbor adjacency matrix from dataframe.
    shp = ps.weights.Rook.from_dataframe(df, geom_col="geometry")

    # See http://bit.ly/2y3HNMh
    adjacency = shp.full()[0]

    perims = []
    neighbors = []

    # Iterate over adjacency matrix
    for i, _ in enumerate(adjacency):
        row = []
        for j, _ in enumerate(adjacency):
            adj = adjacency[i][j]

            # If block i is adjacent to block j, append their shared perimeter
            # to the list of perimeters; additionally, change the [i][j]th matrix
            # entry to j (to represent actual adjacency).
            if adj == 1:
                row.append(df["perimeter"][j])
                adjacency[i][j] = j

        perims.append(row)

    # Strip out zeros from adjacency list.
    for row in adjacency:
        neighbors.append([i for i in row if i != 0])

    return neighbors, perims, list(df[name_of_geoid_col])


if __name__ == "__main__":
    ingest("testData/testData.shp", "CD")
