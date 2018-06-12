from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph, get_list_of_data, add_data_to_graph
import matplotlib.pyplot as plt
import networkx as nx

def main():
    G = construct_graph(*ingest("./../tests/data/test/testData.shp", "CD"))

    data1 = get_list_of_data('testData/test_pop_data.csv', 'POP')
    data2 = get_list_of_data('testData/testData.shp', 'CD')

    add_data_to_graph(data1, G, 'POP')
    add_data_to_graph(data2, G, 'CD2')

    print(G.nodes(data=True))
    nx.draw(G)
    plt.show()

if __name__ == "__main__":
    main()
