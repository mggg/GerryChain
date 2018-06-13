import networkx as nx


def is_valid(graph):
    '''

    :param graph: The graph object you are working on.
    :return: A list of booleans to state if the sub graph is connected.
    '''
    # Creates a dictionary where the key is the district and the value is
    # a list of VTDs that belong to that district
    district_list = {}
    for nodes in graph.nodes.data('CD'):
        dist = int(nodes[1])
        if dist in district_list:
            district_list[dist].append(nodes[0])
        else:
            district_list[dist] = [nodes[0]]

    # Checks if the subgraph of one district is connected(contiguous)
    dist_contig = []
    for key in district_list:
        tmp = graph.subgraph(district_list[key])
        dist_contig.append(nx.is_connected(tmp))
    return dist_contig
