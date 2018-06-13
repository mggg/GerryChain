import pysal as ps
import geopandas as gp


def ingest(filepath, name_of_geoid_col):
    """Generate (rook) neighbor and perimeter information from a shapefile.

    :filepath: Path to input shapefile location.

    :returns: Tuple (neighbors, perims, geoid_col) to be passed to :func:`.make_graph`. `neighbors` is a dictionary of (id, [adj_ids\). `perims` is a list of perimeters numbered sequentially. `geoid_col` is a list of the geoids of shapes.

    """
    df = gp.read_file(filepath)

    perimeters = df["geometry"].apply(lambda shape: shape.length).tolist()

    # Dumb stopgap to account for silly non-shared perimeter behavior.
    perimeters = [perimeters] * len(df)
    rook = ps.weights.Rook.from_dataframe(df, geom_col="geometry")

    return rook.neighbors, perimeters, df[name_of_geoid_col].tolist()


if __name__ == "__main__":
    ingest("testData/testData.shp", "CD")
