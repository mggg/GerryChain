from unittest.mock import MagicMock

import geopandas as gp
import pytest
from shapely.geometry import Polygon

from gerrychain import Graph, Partition


@pytest.fixture
def partition():
    graph = Graph([(0, 1), (1, 3), (2, 3), (0, 2)])
    return Partition(graph, {0: 1, 1: 1, 2: 2, 3: 2})


@pytest.fixture
def geodataframe():
    a = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
    b = Polygon([(0, 1), (0, 2), (1, 2), (1, 1)])
    c = Polygon([(1, 0), (1, 1), (2, 1), (2, 0)])
    d = Polygon([(1, 1), (1, 2), (2, 2), (2, 1)])
    df = gp.GeoDataFrame({"ID": ["a", "b", "c", "d"], "geometry": [a, b, c, d]})
    df.crs = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
    return df


class TestPartitionPlotting:
    def test_can_plot(self, geodataframe, partition):
        mock_plot = MagicMock()
        gp.GeoDataFrame.plot = mock_plot
        partition.plot(geodataframe)
        assert mock_plot.call_count == 1

    def test_raises_typeerror_for_mismatched_indices(self, geodataframe, partition):
        df = geodataframe.set_index("ID")
        with pytest.raises(TypeError):
            partition.plot(df)

    def test_can_plot_using_geoseries(self, geodataframe, partition):
        mock_plot = MagicMock()
        gp.GeoDataFrame.plot = mock_plot
        partition.plot(geodataframe.geometry)
        assert mock_plot.call_count == 1

    def test_can_pass_kwargs_to_plot(self, geodataframe, partition):
        mock_plot = MagicMock()
        gp.GeoDataFrame.plot = mock_plot

        partition.plot(geodataframe, cmap="viridis")

        args, kwargs = mock_plot.call_args
        assert kwargs["cmap"] == "viridis"

    def test_calls_with_column_as_a_string(self, geodataframe, partition):
        mock_plot = MagicMock()
        gp.GeoDataFrame.plot = mock_plot

        partition.plot(geodataframe)

        args, kwargs = mock_plot.call_args
        assert isinstance(kwargs["column"], str)

    def test_uses_graph_geometries_by_default(self, geodataframe):
        mock_plot = MagicMock()
        gp.GeoDataFrame.plot = mock_plot

        graph = Graph.from_geodataframe(geodataframe)
        partition = Partition(graph=graph, assignment={node: 0 for node in graph})
        partition.plot()
        assert mock_plot.call_count == 1
