
from rundmcmc.cli import cli
from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph
import matplotlib.pyplot as plt
import networkx as nx

def main():
    G = construct_graph(*ingest("./../tests/data/test/testData.shp"))
    nx.draw(G)
    plt.show()


if __name__ == "__main__":
    main()
