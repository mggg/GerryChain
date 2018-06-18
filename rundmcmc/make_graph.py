import networkx
import pandas as pd
import geopandas as gp
import pysal as ps


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



def add_data_to_graph(df, graph, col_names, id_col=None):
    '''Add columns of a dataframe to a graph based on ids.

    :df: Dataframe containing given column.
    :graph: Networkx object containing appropriately labeled nodes.
    :col_names: List of dataframe column names to add.
    :id_col: The column name to pull graph ids from. The row from this id will
             be assigned to the corresponding node in the graph. If `None`,
             then the data is assigned to consecutive integer labels 0, 1, ...,
             len(graph) - 1.

    '''
    if id_col:
        for row in df.itertuples():
            node = getattr(row, id_col)
            for name in col_names:
                data = getattr(row, name)
                graph.nodes[node][name] = data
    else:
        for i, row in enumerate(df.itertuples()):
            node = getattr(row, id_col)
            for name in col_names:
                data = getattr(row, name)
                graph.nodes[i][name] = data


def construct_graph(df, geoid_col=None):
    '''Construct initial graph from information about neighboring VTDs.

    :df: Geopandas dataframe.
    :returns: Networkx Graph.

    '''
    if geoid_col is not None:
        df = df.set_index(geoid_col)

    # Generate rook neighbor lists from dataframe.
    neighbors = ps.weights.Rook.from_dataframe(
        df, geom_col="geometry").neighbors

    vtds = {}

    for shape in neighbors:
        vtds[shape] = {}

        for neighbor in neighbors[shape]:
            shared_perim = df.loc[shape, "geometry"].intersection(
                df.loc[neighbor, "geometry"]).length

            vtds[shape][neighbor] = {'shared_perim': shared_perim}

    graph = networkx.from_dict_of_dicts(vtds)

    return graph


def get_assignment_dict(df, key_col, val_col):
    """Return a dictionary of {key: val} pairs from the dataframe.

    :df: Dataframe.
    :key_col: Column name to be used for keys.
    :val_col: Column name to be used for values.
    :returns: Dictionary of {key: val} pairs from the given columns.

    """
    dict_df = df.set_index(key_col)
    return dict_df[val_col].to_dict()
