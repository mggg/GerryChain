
import geopandas as gp
import pysal as ps
import time
from rundmcmc.make_graph import construct_graph


def report(prorated=None, location="./testData/mo_dists.geojson"):
    print("Generating adjacencies...")
    start = time.time()
    df = gp.read_file(location)
    graph = construct_graph(df)
    end = time.time()
    print("Finished in {} seconds".format(str(end - start)))
    print(list(graph.adjacency()))



if __name__ == "__main__":
    report()