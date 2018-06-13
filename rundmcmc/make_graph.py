import sys
import networkx


def add_data_to_graph(your_data, graph, data_name):
    '''Adds data to the graph after it has been constructed.

    :your_data: A column with the data you would like to add to the nodes(VTDs).
    :graph: The graph you constructed and want to run chain on.
    :data_name: How you would like the data on the node layer labeled.

    '''
    # Check to make sure threre is a one-to-one between data and VTDs
    if len(graph) != len(your_data):
        print("Your column length doesn't match the number of nodes!")
        sys.exit(1)

    # Adding data to the nodes
    for i, j in enumerate(graph.nodes()):
        graph.nodes[j][data_name] = your_data[i]


def construct_graph(lists_of_neighbors, lists_of_perims, district_list):
    '''Constructs your starting graph to run chain on

    :lists_of_neighbors: A list of lists stating the neighbors of each VTD.
    :lists_of_perims: List of lists of perimeters.
    :district_list: List of congressional districts associated to each node(VTD).

    '''
    graph = networkx.Graph()

    # Creating the graph itself
    for vtd, list_nbs in enumerate(lists_of_neighbors):
        for d in list_nbs:
            graph.add_edge(vtd, d)

    # Add perims to edges
    for i, nbs in enumerate(lists_of_neighbors):
        for x, nb in enumerate(nbs):
            graph.add_edge(i, nb, perim=lists_of_perims[i][x])

    # Add districts to each node(VTD)
    for i, j in enumerate(graph.nodes()):
        graph.nodes[j]['CD'] = district_list[i]

    return graph
