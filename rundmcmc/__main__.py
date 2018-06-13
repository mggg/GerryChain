from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph, get_list_of_data, add_data_to_graph, pull_districts
from rundmcmc.validity import contiguous
import matplotlib.pyplot as plt
import networkx as nx


def main():
    G = construct_graph(*ingest("testData/wyoming_test.shp", "GEOID"))
    cd_data = get_list_of_data('testData/wyoming_test.shp', 'CD')
    add_data_to_graph(cd_data, G, 'CD')

    print(contiguous(G))
    print(G.nodes(data=True))
    print(pull_districts(G, 'CD'))
    nx.draw(G)
    plt.show()


if __name__ == "__main__":
    main()
