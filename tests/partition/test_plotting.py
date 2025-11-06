from unittest.mock import MagicMock

import geopandas as gp
import pytest
from shapely.geometry import Polygon
import networkx

from gerrychain import Graph, Partition


@pytest.fixture
def partition():
    nx_graph = networkx.Graph([(0, 1), (1, 3), (2, 3), (0, 2)])
    graph = Graph.from_networkx(nx_graph)
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

        # frm: TODO: Testing: how to handle geometry?
        # 
        # Originally, the following statement blew up because we do not copy
        #               geometry data from NX to RX when we convert to RX.
        #
        # I said at the time:
        #               Need to grok what the right way to deal with geometry 
        #               data is (is it only an issue for from_geodataframe() or
        #               are there other ways a geometry value might be set?)
        #
        # Peter comments (from PR):
        #
        # The geometry data should only exist on the attached geodataframe. 
        # In fact, if there is no "geometry" column in the dataframe, this call 
        # should fail.
        # 
        # Fixing the plotting functions is a low-priority. I need to set up 
        # snapshot tests for these anyway, so if you find working with 
        # matplotlib a PITA (because it is), then don't worry about the 
        # plotting functions for now.
        # 
        # Worst-case scenario, I can just add some temporary verbage to 
        # readthedocs telling people to use
        # 
        # my_partition.df.plot()

        # Which will just use all of the plotting stuff that Pandas has set up internally.

        partition.plot()
        assert mock_plot.call_count == 1
        