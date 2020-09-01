import pathlib
from tempfile import TemporaryDirectory
from unittest.mock import patch

import geopandas as gp
import pandas
import pytest
from shapely.geometry import Polygon

from gerrychain.graph import Graph
from gerrychain.graph.geo import GeometryError


@pytest.fixture
def geodataframe():
    a = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
    b = Polygon([(0, 1), (0, 2), (1, 2), (1, 1)])
    c = Polygon([(1, 0), (1, 1), (2, 1), (2, 0)])
    d = Polygon([(1, 1), (1, 2), (2, 2), (2, 1)])
    df = gp.GeoDataFrame({"ID": ["a", "b", "c", "d"], "geometry": [a, b, c, d]})
    df.crs = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
    return df


@pytest.fixture
def gdf_with_data(geodataframe):
    geodataframe["data"] = list(range(len(geodataframe)))
    geodataframe["data2"] = list(range(len(geodataframe)))
    return geodataframe


@pytest.fixture
def geodataframe_with_boundary():
    """
    abe
    ade
    ace
    """
    a = Polygon([(0, 0), (0, 1), (0, 2), (0, 3), (1, 3), (1, 2), (1, 1), (1, 0)])
    b = Polygon([(1, 2), (1, 3), (2, 3), (2, 2)])
    c = Polygon([(1, 0), (1, 1), (2, 1), (2, 0)])
    d = Polygon([(1, 1), (1, 2), (2, 2), (2, 1)])
    e = Polygon([(2, 0), (2, 1), (2, 2), (2, 3), (3, 3), (3, 2), (3, 1), (3, 0)])
    df = gp.GeoDataFrame({"ID": ["a", "b", "c", "d", "e"], "geometry": [a, b, c, d, e]})
    df.crs = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
    return df


@pytest.fixture
def shapefile(gdf_with_data):
    with TemporaryDirectory() as d:
        filepath = pathlib.Path(d) / "temp.shp"
        filename = str(filepath.absolute())
        gdf_with_data.to_file(filename)
        yield filename


@pytest.fixture
def target_file():
    with TemporaryDirectory() as d:
        filepath = pathlib.Path(d) / "temp.shp"
        filename = str(filepath.absolute())
        yield filename


def test_add_data_to_graph_can_handle_column_names_that_start_with_numbers():
    graph = Graph([("01", "02"), ("02", "03"), ("03", "01")])
    df = pandas.DataFrame({"16SenDVote": [20, 30, 50], "node": ["01", "02", "03"]})
    df = df.set_index("node")

    graph.add_data(df, ["16SenDVote"])

    assert graph.nodes["01"]["16SenDVote"] == 20
    assert graph.nodes["02"]["16SenDVote"] == 30
    assert graph.nodes["03"]["16SenDVote"] == 50


def test_join_can_handle_right_index():
    graph = Graph([("01", "02"), ("02", "03"), ("03", "01")])
    df = pandas.DataFrame({"16SenDVote": [20, 30, 50], "node": ["01", "02", "03"]})

    graph.join(df, ["16SenDVote"], right_index="node")

    assert graph.nodes["01"]["16SenDVote"] == 20
    assert graph.nodes["02"]["16SenDVote"] == 30
    assert graph.nodes["03"]["16SenDVote"] == 50


def test_make_graph_from_dataframe_creates_graph(geodataframe):
    graph = Graph.from_geodataframe(geodataframe)
    assert isinstance(graph, Graph)


def test_make_graph_from_dataframe_preserves_df_index(geodataframe):
    df = geodataframe.set_index("ID")
    graph = Graph.from_geodataframe(df)
    assert set(graph.nodes) == {"a", "b", "c", "d"}


def test_make_graph_from_dataframe_gives_correct_graph(geodataframe):
    df = geodataframe.set_index("ID")
    graph = Graph.from_geodataframe(df)

    assert edge_set_equal(
        set(graph.edges), {("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")}
    )


def test_make_graph_works_with_queen_adjacency(geodataframe):
    df = geodataframe.set_index("ID")
    graph = Graph.from_geodataframe(df, adjacency="queen")

    assert edge_set_equal(
        set(graph.edges),
        {("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("a", "d"), ("b", "c")},
    )


def test_can_pass_queen_or_rook_strings_to_control_adjacency(geodataframe):
    df = geodataframe.set_index("ID")
    graph = Graph.from_geodataframe(df, adjacency="queen")

    assert edge_set_equal(
        set(graph.edges),
        {("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("a", "d"), ("b", "c")},
    )


def test_can_insist_on_not_reprojecting(geodataframe):
    df = geodataframe.set_index("ID")
    graph = Graph.from_geodataframe(df, reproject=False)

    for node in ("a", "b", "c", "d"):
        assert graph.nodes[node]["area"] == 1

    for edge in graph.edges:
        assert graph.edges[edge]["shared_perim"] == 1


def test_does_not_reproject_by_default(geodataframe):
    df = geodataframe.set_index("ID")
    graph = Graph.from_geodataframe(df)

    for node in ("a", "b", "c", "d"):
        assert graph.nodes[node]["area"] == 1.0

    for edge in graph.edges:
        assert graph.edges[edge]["shared_perim"] == 1.0


def test_reproject(geodataframe):
    # I don't know what the areas and perimeters are in UTM for these made-up polygons,
    # but I'm pretty sure they're not 1.
    df = geodataframe.set_index("ID")
    graph = Graph.from_geodataframe(df, reproject=True)

    for node in ("a", "b", "c", "d"):
        assert graph.nodes[node]["area"] != 1

    for edge in graph.edges:
        assert graph.edges[edge]["shared_perim"] != 1


def test_identifies_boundary_nodes(geodataframe_with_boundary):
    df = geodataframe_with_boundary.set_index("ID")
    graph = Graph.from_geodataframe(df)

    for node in ("a", "b", "c", "e"):
        assert graph.nodes[node]["boundary_node"]
    assert not graph.nodes["d"]["boundary_node"]


def test_computes_boundary_perims(geodataframe_with_boundary):
    df = geodataframe_with_boundary.set_index("ID")
    graph = Graph.from_geodataframe(df, reproject=False)

    expected = {"a": 5, "e": 5, "b": 1, "c": 1}

    for node, value in expected.items():
        assert graph.nodes[node]["boundary_perim"] == value


def edge_set_equal(set1, set2):
    return {(y, x) for x, y in set1} | set1 == {(y, x) for x, y in set2} | set2


def test_from_file_adds_all_data_by_default(shapefile):
    graph = Graph.from_file(shapefile)

    assert all("data" in node_data for node_data in graph.nodes.values())
    assert all("data2" in node_data for node_data in graph.nodes.values())


def test_from_file_and_then_to_json_does_not_error(shapefile, target_file):
    graph = Graph.from_file(shapefile)

    # Even the geometry column is copied to the graph
    assert all("geometry" in node_data for node_data in graph.nodes.values())

    graph.to_json(target_file)


def test_from_file_and_then_to_json_with_geometries(shapefile, target_file):
    graph = Graph.from_file(shapefile)

    # Even the geometry column is copied to the graph
    assert all("geometry" in node_data for node_data in graph.nodes.values())

    graph.to_json(target_file, include_geometries_as_geojson=True)


def test_graph_warns_for_islands():
    graph = Graph()
    graph.add_node(0)

    with pytest.warns(Warning):
        graph.warn_for_islands()


def test_graph_raises_if_crs_is_missing_when_reprojecting(geodataframe):
    geodataframe.crs = None

    with pytest.raises(ValueError):
        Graph.from_geodataframe(geodataframe, reproject=True)


def test_raises_geometry_error_if_invalid_geometry(shapefile):
    with patch("gerrychain.graph.geo.explain_validity") as explain:
        explain.return_value = "Invalid geometry"
        with pytest.raises(GeometryError):
            Graph.from_file(shapefile, ignore_errors=False)


def test_can_ignore_errors_while_making_graph(shapefile):
    with patch("gerrychain.graph.geo.explain_validity") as explain:
        explain.return_value = "Invalid geometry"
        assert Graph.from_file(shapefile, ignore_errors=True)


def test_data_and_geometry(gdf_with_data):
    df = gdf_with_data
    graph = Graph.from_geodataframe(df, cols_to_add=["data","data2"])
    assert graph.geometry is df.geometry
    #graph.add_data(df[["data"]])
    assert (graph.data["data"] == df["data"]).all()
    #graph.add_data(df[["data2"]])
    assert list(graph.data.columns) == ["data", "data2"]
