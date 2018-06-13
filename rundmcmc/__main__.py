from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph, get_list_of_data, add_data_to_graph
from rundmcmc.validity import is_valid
import matplotlib.pyplot as plt
import networkx as nx


def main():
    G = construct_graph(*ingest("testData/wyoming_test.shp", "GEOID"))
    cd_data = get_list_of_data('testData/wyoming_test.shp', 'CD')
    add_data_to_graph(cd_data, G, 'CD')

    print(is_valid(G))
    print(G.nodes(data=True))
    nx.draw(G)
    plt.show()


if __name__ == "__main__":
    main()
