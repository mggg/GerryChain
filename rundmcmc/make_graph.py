from graph_tool import Graph
import pandas as pd
import geopandas as gp
import numpy as np


def get_list_of_data(filepath, col_name):
    '''Pull a column data from a shape or CSV file.

    :param filepath: The path to where your data is located.

    :param col_name: A list of the columns of data you want to grab.
    :return: A list of the data you have specified.

    '''
    # Checks if you have inputed a csv or shp file then captures the data
    data = []
    if filepath.split('.')[-1] == 'csv':
        df = pd.read_csv(filepath)
        for i in col_name:
            data.append(df[i])
        return data
    if filepath.split('.')[-1] == 'shp':
        df = gp.read_file(filepath)
        for i in col_name:
            data.append(df[i])
        return data


def add_data_to_graph(data, graph, data_name):
    '''Add a list of data to graph nodes.

    :data: A column with the data you would like to add to the nodes(VTDs).
    :graph: The graph you constructed and want to run chain on.

    :data_name: A list of the attribute names you are adding.

    '''
    # Check to make sure there is a one-to-one between data and VTDs
    for i, _ in enumerate(data_name):
        if graph.num_vertices() != len(data[i]):
            raise ValueError("Your column length doesn't match the number of nodes!")

    # Adding data to the nodes
        for i, _ in enumerate(data_name):
            # get the graph-tool value type to create the property map for the data
            dtype = get_type(data[i][0])
            vdata = graph.new_vertex_property(dtype)

            # can't vectorize assignment of nonscalar data types
            if dtype == "string":
                for j in range(len(data[i])):
                    vdata[graph.vertex(i)] = data[i][j]
            else:
                # assign data as a vector, very slick
                graph.vertex_properties[data_name[i]] = vdata
                vdata.a = data[i]


def construct_graph(lists_of_neighbors, lists_of_perims, geoid):
    '''Construct initial graph from neighbor and perimeter information.

    :lists_of_neighbors: A list of lists stating the neighbors of each VTD.
    :lists_of_perims: List of lists of perimeters.
    :district_list: List of congressional districts associated to each node(VTD).
    :returns: Networkx Graph.

    The three arguments can be built from shape files with :func:`.ingest`.

    '''
    graph = Graph()

    graph.add_vertex(len(lists_of_neighbors))
    # Creating the graph itself
    for vtd, list_nbs in enumerate(lists_of_neighbors):
        for d in list_nbs:
            e = graph.add_edge(graph.vertex(vtd), graph.vertex(d))

    shared_perim = graph.new_edge_property("double")
    graph.edge_properties["shared_perim"] = shared_perim
    # Add perims to edges
    for i, nbs in enumerate(lists_of_neighbors):
        for x, nb in enumerate(nbs):
            e = graph.edge(graph.vertex(i), graph.vertex(nb))
            graph.edge_properties["shared_perim"][e] = lists_of_perims[i][x]

    # Add GEOID to each node(VTD)
    vgeoid = graph.new_vertex_property("string")
    graph.vertex_properties["GEOID"] = vgeoid
    for i in range(len(geoid)):
        vgeoid[graph.vertex(i)] = geoid[i]

    return graph


def pull_districts(graph, cd_identifier):
    '''Creates dictionary of nodes to their CD.

    :param graph: The graph object you are working on.
    :param cd_identifier: How the congressional district is labeled on your graph.
    :return: A dictionary.
    '''
    # creates a dictionary and iterates over the nodes to add node to CD.
    nodes = {}
    # get the vertex property map of the identifier
    vpop = graph.vertex_properties[cd_identifier]
    for i in range(graph.num_vertices()):
        nodes[i] = vpop[graph.vertex(i)]
    return nodes


def get_type(data):
    if isinstance(data, int) or isinstance(data, np.int64):  # type(data) == type(np.int64(2)):
        return "int"
    elif isinstance(data, float):
        return "float"
    elif isinstance(data, str):
        return "string"
    else:
        print(type(data))
        return "fail"
