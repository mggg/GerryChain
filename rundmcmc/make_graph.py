import networkx
import pandas as pd
import geopandas as gp
import pysal
import json
from networkx.readwrite import json_graph
from shapely.ops import cascaded_union
import os.path


def get_list_of_data(filepath, col_name, geoid=None):
    """Pull a column data from a CSV file or any fiona-supported file.

    :filepath: Path to datafile.
    :col_name: List of column names to grab.
    :returns: List of data.

    """
    # Checks if you have inputed a csv or shp file then captures the data
    extension = os.path.splitext(filepath)

    if extension.lower() == "csv":
        df = pd.read_csv(filepath)
    else:
        df = gp.read_file(filepath)

    if geoid is None:
        geoid = "sampleIndex"
        df[geoid] = range(len(df))

    data = pd.DataFrame({geoid: df[geoid]})
    for i in col_name:
        data[i] = df[i]

    return data


def add_data_to_graph(df, graph, col_names, id_column=None):
    """Add columns of a dataframe to a graph using the the index as node ids.

    :df: Dataframe containing given columns.
    :graph: NetworkX graph containing appropriately labeled nodes.
    :col_names: List of dataframe column names to add.
    :returns: Nothing.

    """
    if id_column:
        indexed_df = df.set_index(id_column)
    else:
        indexed_df = df

    column_dictionaries = indexed_df[col_names].to_dict('index')
    networkx.set_node_attributes(graph, column_dictionaries)


def add_boundary_perimeters(graph, neighbors, df):
    """
    Add shared perimeter between nodes and the total geometry boundary.

    :graph: NetworkX graph.
    :neighbors: Adjacency information generated from pysal.
    :df: Geodataframe containing geometry information.
    :returns: The updated graph.

    """
    all_units = df['geometry']
    # creates one shape of the entire state to compare outer boundaries against
    boundary = gp.GeoSeries(cascaded_union(all_units).boundary)

    # finds if it intersects on outside and sets
    # a 'boundary_node' attribute to true if it does
    # if it is set to true, it also adds how much shared
    # perimiter they have to a 'boundary_perim' attribute
    for node in neighbors:
        graph.node[node]['boundary_node'] = boundary.intersects(
            df.loc[node, "geometry"]).bool()

        if boundary.intersects(df.loc[node, "geometry"]).bool():
            graph.node[node]['boundary_perim'] = float(
                boundary.intersection(df.loc[node, "geometry"]).length)

    return graph


def neighbors_with_shared_perimeters(neighbors, df):
    """Construct a graph with shared perimeter between neighbors on the edges.

    :neighbors: Adjacency information generated from pysal.
    :df: Geodataframe containing geometry information.
    :returns: NetworkX graph.

    """
    vtds = {}

    for shape in neighbors:
        vtds[shape] = {}

        for neighbor in neighbors[shape]:
            shared_perim = df.loc[shape, "geometry"].intersection(
                df.loc[neighbor, "geometry"]).length
            vtds[shape][neighbor] = {'shared_perim': shared_perim}

    return networkx.from_dict_of_dicts(vtds)


def construct_graph_from_df(df, id_column=None, cols_to_add=None):
    """Construct initial graph from information about neighboring VTDs.

    :df: Geopandas dataframe.
    :returns: NetworkX Graph.

    """
    if id_column is not None:
        df = df.set_index(id_column)

    # Generate rook neighbor lists from dataframe.
    neighbors = pysal.weights.Rook.from_dataframe(
        df, geom_col="geometry").neighbors

    graph = neighbors_with_shared_perimeters(neighbors, df)

    add_boundary_perimeters(graph, neighbors, df)

    if cols_to_add is not None:
        add_data_to_graph(df, graph, cols_to_add)

    return graph


def construct_graph_from_json(json_file):
    """Construct initial graph from networkx.json_graph adjacency JSON format.

    :json_file: Path to JSON file.
    :returns: NetworkX graph.

    """
    with open(json_file) as f:
        data = json.load(f)

    return json_graph.adjacency_graph(data)


def construct_graph_from_file(filename, id_column=None, cols_to_add=None):
    """Constuct initial graph from any file that fiona can read.

    This can load any file format supported by GeoPandas, which is everything
    that the fiona library supports.

    :filename: File to read.
    :id_column: Unique identifier column for the data units; used as node ids in the graph.
    :cols_to_add: List of column names from file of data to be added to each node.
    :returns: NetworkX Graph.

    """
    df = gp.read_file(filename)

    return construct_graph_from_df(df, id_column, cols_to_add)


def construct_graph(data_source, id_column=None, data_cols=None, data_source_type="fiona"):
    """
    Construct initial graph from given data source.

    :data_source: Data from which to create graph ("fiona", "geo_data_frame", or "json".).
    :id_column: Name of unique identifier for basic data units.
    :data_cols: Any extra data contained in data_source to be added to nodes of graph.
    :data_source_type: String specifying the type of data_source;
                       can be one of "fiona", "json", or "geo_data_frame".
    :returns: NetworkX graph.

    The supported data types are:

        - "fiona": The filename of any file that geopandas (i.e., fiona) can
                    read. This includes SHAPE files, GeoJSON, and others. For a
                    full list, check `fiona.supported_drivers`.

        - "json": A json file formatted by NetworkX's adjacency graph method.

        - "geo_data_frame": A geopandas dataframe.

    """
    if data_source_type == "fiona":
        return construct_graph_from_file(data_source, id_column, data_cols)

    elif data_source_type == "json":
        return construct_graph_from_json(data_source)

    elif data_source_type == "geo_data_frame":
        return construct_graph_from_df(data_source, id_column, data_cols)


def get_assignment_dict_from_df(df, key_col, val_col):
    """Grab assignment dictionary from the given columns of the dataframe.

    :df: Dataframe.
    :key_col: Column name to be used for keys.
    :val_col: Column name to be used for values.
    :returns: Dictionary of {key: val} pairs from the given columns.

    """
    dict_df = df.set_index(key_col)
    return dict_df[val_col].to_dict()


def get_assignment_dict_from_graph(graph, assignment_attribute):
    """Grab assignment dictionary from the given attributes of the graph.

    :graph: NetworkX graph.
    :assignment_attribute: Attribute available on all nodes.
    :returns: Dictionary of {node_id: attribute} pairs.

    """
    return networkx.get_node_attributes(graph, assignment_attribute)
