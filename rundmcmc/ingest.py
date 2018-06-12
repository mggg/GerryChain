
import networkx as nx
import pysal as ps
import geopandas as gp
import matplotlib.pyplot as plt


def ingest(filepath="./../data/test/testData.shp"):
    """
        Reads in a shapefile through PySAL, and generates an
        adjacency matrix (rook adjacency). Then, load the converted
        NumPy data from PySAL into NetworkX.
    """
    shp = ps.rook_from_shapefile(filepath)
    return nx.Graph(shp.full()[0])


if __name__ == "__main__":
    ingest()
