import pysal as ps
import geopandas as gp


def ingest(filepath, name_of_geoid_col=None):
    """Generate (rook) neighbor and perimeter information from a shapefile.

    :filepath: Path to input shapefile location.
    :name_of_geoid_col: Name of column that contains the unique name for each shape.
    :returns: Dict of dicts of dicts. There is a dict for each shape, which
        contains a dict for each neighbor, which contains a dict of attributes
        (e.g., shared perimeter) about the corresponding edge. Output will be passed
        to :func:`.make_graph`.

    """

    df = gp.read_file(filepath)
    if name_of_geoid_col is not None:
        df = df.set_index(name_of_geoid_col)

    # Generate rook neighbor lists from dataframe.
    neighbors = ps.weights.Rook.from_dataframe(
        df, geom_col="geometry").neighbors

    vtds = {}

    for shape in neighbors:
        vtds[shape] = {}

        for neighbor in neighbors[shape]:
            shared_perim = df.loc[shape, "geometry"].intersection(
                df.loc[neighbor, "geometry"]).length

            vtds[shape][neighbor] = {'shared_perim': shared_perim}

    return vtds


if __name__ == "__main__":
    ingest("testData/testData.shp", "CD")
