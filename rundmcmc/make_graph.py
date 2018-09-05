import json
import os.path
import warnings
from collections import Counter

import geopandas as gp
import networkx
import pandas as pd
import pysal
from networkx.readwrite import json_graph
from shapely.ops import cascaded_union

import utm


def utm_of_point(point):
    return utm.from_latlon(point.y, point.x)[2]


def identify_utm_zone(df):
    wgs_df = df.to_crs("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
    utm_counts = Counter(utm_of_point(point) for point in wgs_df['geometry'].centroid)
    # most_common returns a list of tuples, and we want the 0,0th entry
    most_common = utm_counts.most_common(1)[0][0]
    return most_common


def reprojected(df):
    utm = identify_utm_zone(df)
    return df.to_crs(f"+proj=utm +zone={utm} +ellps=WGS84 +datum=WGS84 +units=m +no_defs")


def get_list_of_data(filepath, col_name, geoid=None):
    """Pull a column data from a CSV file or any fiona-supported file.

    :filepath: Path to datafile.
    :col_name: List of column names to grab.
    :returns: List of data.

    """
    # Checks if you have inputed a csv or shp file then captures the data
    extension = os.path.splitext(filepath)[-1]

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


def add_data_to_graph(df, graph, col_names, id_col=None):
    """Add columns of a dataframe to a graph using the the index as node ids.

    :df: Dataframe containing given columns.
    :graph: NetworkX graph containing appropriately labeled nodes.
    :col_names: List of dataframe column names to add.
    :returns: Nothing.

    """
    if id_col:
        indexed_df = df.set_index(id_col)
    else:
        indexed_df = df

    for name in col_names:
        df[name] = pd.to_numeric(df[name], errors='coerce')

    df.fillna(0)

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
    # creates one shape of the entire state to compare outer boundaries against
    boundary = cascaded_union(df.geometry).boundary

    intersections = df.intersection(boundary)
    is_boundary = intersections.apply(bool)

    # Add boundary node information to the graph.
    intersection_df = gp.GeoDataFrame(intersections)
    intersection_df["boundary_node"] = is_boundary

    # List-indexing here to get the correct dictionary format for NetworkX.
    attr_dict = intersection_df[["boundary_node"]].to_dict("index")
    networkx.set_node_attributes(graph, attr_dict)

    # For the boundary nodes, set the boundary perimeter.
    boundary_perims = intersections[is_boundary].length
    boundary_perims = gp.GeoDataFrame(boundary_perims)
    boundary_perims.columns = ["boundary_perim"]

    attribute_dict = boundary_perims.to_dict("index")
    networkx.set_node_attributes(graph, attribute_dict)


def neighbors_with_shared_perimeters(neighbors, df):
    """Construct a graph with shared perimeter between neighbors on the edges.

    :neighbors: Adjacency information generated from pysal.
    :df: Geodataframe containing geometry information.
    :returns: NetworkX graph.

    """
    vtds = {}

    geom = df.geometry
    for shape in neighbors:
        shared_perim = geom[neighbors[shape]].intersection(geom[shape]).length
        shared_perim.name = "shared_perim"
        vtds[shape] = pd.DataFrame(shared_perim).to_dict("index")

    return networkx.from_dict_of_dicts(vtds)


def construct_graph_from_df(df_unprojected,
        id_col=None,
        pop_col=None,
        area_col=None,
        district_col=None,
        cols_to_add=None):
    """Construct initial graph from information about neighboring VTDs.

    :df: Geopandas dataframe.
    :returns: NetworkX Graph.

    """
    df = reprojected(df_unprojected)

    if id_col is not None:
        df = df.set_index(id_col)

    # Generate rook neighbor lists from dataframe.
    neighbors = pysal.weights.Rook.from_dataframe(
        df, geom_col=df.geometry.name).neighbors

    graph = neighbors_with_shared_perimeters(neighbors, df)

    add_boundary_perimeters(graph, neighbors, df)

    if cols_to_add is not None:
        add_data_to_graph(df, graph, cols_to_add)

    pops = 0
    p_name = "population"
    if pop_col:
        df[pop_col] = pd.to_numeric(df[pop_col], errors='coerce')
        pops = df[pop_col].to_dict()
        p_name = pop_col
    else:
        warnings.warn("No population column was given, assuming all 0")

    a_name = "areas"
    if area_col:
        areas = df[area_col].to_dict()
        a_name = area_col
    else:
        # This may be slightly expensive, so only do it if we know we have to.
        areas = reprojected(df)['geometry'].area.to_dict()
        warnings.warn("No area column was given, computing from geometry")

    dists = 0
    d_name = "CD"
    if district_col:
        df[district_col] = pd.to_numeric(df[district_col], errors='coerce')

        dists = df[district_col].to_dict()
        d_name = district_col
    else:
        warnings.warn("No district assignment column was given, assuming all 0")

    # add new attribute to all nodes with value 0 used as dummy variable
    networkx.set_node_attributes(graph, name=p_name, values=pops)
    networkx.set_node_attributes(graph, name=a_name, values=areas)
    networkx.set_node_attributes(graph, name=d_name, values=dists)

    return graph


def construct_graph_from_json(json_file, pop_col=None, area_col=None, district_col=None):
    """Construct initial graph from networkx.json_graph adjacency JSON format.

    :json_file: Path to JSON file.
    :returns: NetworkX graph.

    """
    with open(json_file) as f:
        data = json.load(f)

    g = json_graph.adjacency_graph(data)

    networkx.set_node_attributes(g, 'population', 0)
    networkx.set_node_attributes(g, 'areas', 0)
    networkx.set_node_attributes(g, 'CD', 0)

    # add specific values for column names as specified.
    if pop_col:
        p_col = networkx.get_node_attributes(g, pop_col)
        networkx.set_node_attributes(g, name='population', values=p_col)

    if area_col:
        a_col = networkx.get_node_attributes(g, area_col)
        networkx.set_node_attributes(g, name='areas', values=a_col)

    if district_col:
        cd_col = networkx.get_node_attributes(g, district_col)
        networkx.set_node_attributes(g, name='CD', values=cd_col)

    return g


def construct_graph_from_file(filename,
        id_col=None,
        pop_col=None,
        area_col=None,
        district_col=None,
        cols_to_add=None):
    """Constuct initial graph from any file that fiona can read.

    This can load any file format supported by GeoPandas, which is everything
    that the fiona library supports.

    :filename: File to read.
    :id_col: Unique identifier column for the data units; used as node ids in the graph.
    :cols_to_add: List of column names from file of data to be added to each node.
    :returns: NetworkX Graph.

    """
    df = gp.read_file(filename)

    return construct_graph_from_df(df, id_col, pop_col, area_col, district_col, cols_to_add)


def construct_graph(data_source,
        id_col=None,
        pop_col=None,
        area_col=None,
        district_col=None,
        data_cols=None,
        data_source_type="fiona"):
    """
    Construct initial graph from given data source.

    :data_source: Data from which to create graph ("fiona", "geo_data_frame", or "json".).
    :id_col: Name of unique identifier for basic data units.
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
        return construct_graph_from_file(data_source, id_col, pop_col,
                area_col, district_col, data_cols)

    elif data_source_type == "json":
        return construct_graph_from_json(data_source, pop_col,
                area_col, district_col)

    elif data_source_type == "geodataframe":
        return construct_graph_from_df(data_source, id_col, pop_col,
                area_col, district_col, data_cols)

    raise ValueError("unknown data source type: {}".format(data_source_type))


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
