from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph, get_list_of_data, add_data_to_graph
import matplotlib.pyplot as plt
import networkx as nx

def is_valid(graph):
    district_list = {}
    for nodes in graph.nodes.data('CD'):
        dist = int(nodes[1])
        if dist in district_list:
            district_list[dist].append(nodes[0])
        else:
            district_list[dist] = [nodes[0]]


    for key in district_list:
        tmp = graph.subgraph(district_list[key])
        print(nx.is_connected(tmp))




G = construct_graph(*ingest("testData/wyoming_test.shp", "GEOID"))
cd_data = get_list_of_data('testData/wyoming_test.shp', 'CD')
add_data_to_graph(cd_data, G, 'CD')
is_valid(G)
print(G.nodes(data=True))

print(nx.is_connected(G))
