from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph, get_list_of_data, add_data_to_graph
import matplotlib.pyplot as plt
import networkx as nx

def main():
    G = construct_graph(*ingest("testData/testData.shp", "POP"))
    cd_data = get_list_of_data('testData/testData.shp', 'CD')
    add_data_to_graph(cd_data, G, 'CD')

    print(G.nodes(data=True))
    nx.draw(G)
    plt.show()

if __name__ == "__main__":
    main()
