"""
This module provides tools for working with graphs in the context of geographic data.
It extends the functionality of the NetworkX library, adding support for spatial data structures,
geographic projections, and serialization to and from JSON format.

This module is designed to be used in conjunction with geopandas, shapely, and pandas libraries,
facilitating the integration of graph-based algorithms with geographic information systems (GIS).

Note:
This module relies on NetworkX, pandas, and geopandas, which should be installed and
imported as required.
"""

import functools
import json
from typing import Any
import warnings

import networkx
from networkx.classes.function import frozen
from networkx.readwrite import json_graph
import pandas as pd

from .adjacency import neighbors
from .geo import GeometryError, invalid_geometries, reprojected
from typing import List, Iterable, Optional, Set, Tuple


def json_serialize(input_object: Any) -> Optional[int]:
    """
    This function is used to handle one of the common issues that
    appears when trying to convert a pandas dataframe into a JSON
    serializable object. Specifically, it handles the issue of converting
    the pandas int64 to a python int so that JSON can serialize it.
    This is specifically used so that we can write graphs out to JSON
    files.

    :param input_object: The object to be converted
    :type input_object: Any (expected to be a pd.Int64Dtype)

    :returns: The converted pandas object or None if input is not of type
        pd.Int64Dtype
    :rtype: Optional[int]
    """
    if pd.api.types.is_integer_dtype(input_object):  # handle int64
        return int(input_object)

    return None


class Graph(networkx.Graph):
    """
    Represents a graph to be partitioned, extending the :class:`networkx.Graph`.

    This class includes additional class methods for constructing graphs from shapefiles,
    and for saving and loading graphs in JSON format.
    """

    def __repr__(self):
        return "<Graph [{} nodes, {} edges]>".format(len(self.nodes), len(self.edges))

    @classmethod
    def from_networkx(cls, graph: networkx.Graph) -> "Graph":
        """
        Create a Graph instance from a networkx.Graph object.

        :param graph: The networkx graph to be converted.
        :type graph: networkx.Graph

        :returns: The converted graph as an instance of this class.
        :rtype: Graph
        """
        g = cls(graph)
        return g

    @classmethod
    def from_json(cls, json_file: str) -> "Graph":
        """
        Load a graph from a JSON file in the NetworkX json_graph format.

        :param json_file: Path to JSON file.
        :type json_file: str

        :returns: The loaded graph as an instance of this class.
        :rtype: Graph
        """
        with open(json_file) as f:
            data = json.load(f)
        g = json_graph.adjacency_graph(data)
        graph = cls.from_networkx(g)
        graph.issue_warnings()
        return graph

    def to_json(
        self, json_file: str, *, include_geometries_as_geojson: bool = False
    ) -> None:
        """
        Save a graph to a JSON file in the NetworkX json_graph format.

        :param json_file: Path to target JSON file.
        :type json_file: str
        :param bool include_geometry_as_geojson: Whether to include
            any :mod:`shapely` geometry objects encountered in the graph's node
            attributes as GeoJSON. The default (``False``) behavior is to remove
            all geometry objects because they are not serializable. Including the
            GeoJSON will result in a much larger JSON file.
        :type include_geometries_as_geojson: bool, optional

        :returns: None
        """
        data = json_graph.adjacency_data(self)

        if include_geometries_as_geojson:
            convert_geometries_to_geojson(data)
        else:
            remove_geometries(data)

        with open(json_file, "w") as f:
            json.dump(data, f, default=json_serialize)

    @classmethod
    def from_file(
        cls,
        filename: str,
        adjacency: str = "rook",
        cols_to_add: Optional[List[str]] = None,
        reproject: bool = False,
        ignore_errors: bool = False,
    ) -> "Graph":
        """
        Create a :class:`Graph` from a shapefile (or GeoPackage, or GeoJSON, or
        any other library that :mod:`geopandas` can read. See :meth:`from_geodataframe`
        for more details.

        :param filename: Path to the shapefile / GeoPackage / GeoJSON / etc.
        :type filename: str
        :param adjacency: The adjacency type to use ("rook" or "queen"). Default is "rook"
        :type adjacency: str, optional
        :param cols_to_add: The names of the columns that you want to
            add to the graph as node attributes. Default is None.
        :type cols_to_add: Optional[List[str]], optional
        :param reproject: Whether to reproject to a UTM projection before
            creating the graph. Default is False.
        :type reproject: bool, optional
        :param ignore_errors: Whether to ignore all invalid geometries and try to continue
            creating the graph. Default is False.
        :type ignore_errors: bool, optional

        :returns: The Graph object of the geometries from `filename`.
        :rtype: Graph

        .. Warning::

            This method requires the optional ``geopandas`` dependency.
            So please install ``gerrychain`` with the ``geo`` extra
            via the command:

            .. code-block:: console

                pip install gerrychain[geo]

            or install ``geopandas`` separately.
        """
        import geopandas as gp

        df = gp.read_file(filename)
        graph = cls.from_geodataframe(
            df,
            adjacency=adjacency,
            cols_to_add=cols_to_add,
            reproject=reproject,
            ignore_errors=ignore_errors,
        )
        graph.graph["crs"] = df.crs.to_json()
        return graph

    @classmethod
    def from_geodataframe(
        cls,
        dataframe: pd.DataFrame,
        adjacency: str = "rook",
        cols_to_add: Optional[List[str]] = None,
        reproject: bool = False,
        ignore_errors: bool = False,
        crs_override: Optional[str | int] = None,
    ) -> "Graph":
        """
        Creates the adjacency :class:`Graph` of geometries described by `dataframe`.
        The areas of the polygons are included as node attributes (with key `area`).
        The shared perimeter of neighboring polygons are included as edge attributes
        (with key `shared_perim`).
        Nodes corresponding to polygons on the boundary of the union of all the geometries
        (e.g., the state, if your dataframe describes VTDs) have a `boundary_node` attribute
        (set to `True`) and a `boundary_perim` attribute with the length of this "exterior"
        boundary.

        By default, areas and lengths are computed in a UTM projection suitable for the
        geometries. This prevents the bizarro area and perimeter values that show up when
        you accidentally do computations in Longitude-Latitude coordinates. If the user
        specifies `reproject=False`, then the areas and lengths will be computed in the
        GeoDataFrame's current coordinate reference system. This option is for users who
        have a preferred CRS they would like to use.

        :param dataframe: The GeoDateFrame to convert
        :type dataframe: :class:`geopandas.GeoDataFrame`
        :param adjacency: The adjacency type to use ("rook" or "queen").
            Default is "rook".
        :type adjacency: str, optional
        :param cols_to_add: The names of the columns that you want to
            add to the graph as node attributes. Default is None.
        :type cols_to_add: Optional[List[str]], optional
        :param reproject: Whether to reproject to a UTM projection before
            creating the graph. Default is ``False``.
        :type reproject: bool, optional
        :param ignore_errors: Whether to ignore all invalid geometries and
            attept to create the graph anyway. Default is ``False``.
        :type ignore_errors: bool, optional
        :param crs_override: Value to override the CRS of the GeoDataFrame.
            Default is None.
        :type crs_override: Optional[str | int], optional

        :returns: The adjacency graph of the geometries from `dataframe`.
        :rtype: Graph
        """
        # Validate geometries before reprojection
        if not ignore_errors:
            invalid = invalid_geometries(dataframe)
            if len(invalid) > 0:
                raise GeometryError(
                    "Invalid geometries at rows {} before "
                    "reprojection. Consider repairing the affected geometries with "
                    "`.buffer(0)`, or pass `ignore_errors=True` to attempt to create "
                    "the graph anyways.".format(invalid)
                )

        # Project the dataframe to an appropriate UTM projection unless
        # explicitly told not to.
        if reproject:
            df = reprojected(dataframe)
            if ignore_errors:
                invalid_reproj = invalid_geometries(df)
                print(invalid_reproj)
                if len(invalid_reproj) > 0:
                    raise GeometryError(
                        "Invalid geometries at rows {} after "
                        "reprojection. Consider reloading the GeoDataFrame with "
                        "`reproject=False` or repairing the affected geometries "
                        "with `.buffer(0)`.".format(invalid_reproj)
                    )
        else:
            df = dataframe

        # Generate dict of dicts of dicts with shared perimeters according
        # to the requested adjacency rule
        adjacencies = neighbors(df, adjacency)
        graph = cls(adjacencies)

        graph.geometry = df.geometry

        graph.issue_warnings()

        # Add "exterior" perimeters to the boundary nodes
        add_boundary_perimeters(graph, df.geometry)

        # Add area data to the nodes
        areas = df.geometry.area.to_dict()
        networkx.set_node_attributes(graph, name="area", values=areas)

        graph.add_data(df, columns=cols_to_add)

        if crs_override is not None:
            df.set_crs(crs_override, inplace=True)

        if df.crs is None:
            warnings.warn(
                "GeoDataFrame has no CRS. Did you forget to set it? "
                "If you're sure this is correct, you can ignore this warning. "
                "Otherwise, please set the CRS using the `crs_override` parameter. "
                "Attempting to proceed without a CRS."
            )
            graph.graph["crs"] = None
        else:
            graph.graph["crs"] = df.crs.to_json()

        return graph

    def lookup(self, node: Any, field: Any) -> Any:
        """
        Lookup a node/field attribute.

        :param node: Node to look up.
        :type node: Any
        :param field: Field to look up.
        :type field: Any

        :returns: The value of the attribute `field` at `node`.
        :rtype: Any
        """
        return self.nodes[node][field]

    @property
    def node_indices(self):
        return set(self.nodes)

    @property
    def edge_indices(self):
        return set(self.edges)

    def add_data(
        self, df: pd.DataFrame, columns: Optional[Iterable[str]] = None
    ) -> None:
        """
        Add columns of a DataFrame to a graph as node attributes
        by matching the DataFrame's index to node ids.

        :param df: Dataframe containing given columns.
        :type df: :class:`pandas.DataFrame`
        :param columns: List of dataframe column names to add. Default is None.
        :type columns: Optional[Iterable[str]], optional

        :returns: None
        """

        if columns is None:
            columns = list(df.columns)

        check_dataframe(df[columns])

        column_dictionaries = df.to_dict("index")
        networkx.set_node_attributes(self, column_dictionaries)

        if hasattr(self, "data"):
            self.data[columns] = df[columns]  # type: ignore
        else:
            self.data = df[columns]

    def join(
        self,
        dataframe: pd.DataFrame,
        columns: Optional[List[str]] = None,
        left_index: Optional[str] = None,
        right_index: Optional[str] = None,
    ) -> None:
        """
        Add data from a dataframe to the graph, matching nodes to rows when
        the node's `left_index` attribute equals the row's `right_index` value.

        :param dataframe: DataFrame.
        :type dataframe: :class:`pandas.DataFrame`
        :columns: The columns whose data you wish to add to the graph.
            If not provided, all columns are added. Default is None.
        :type columns: Optional[List[str]], optional
        :left_index: The node attribute used to match nodes to rows.
            If not provided, node IDs are used. Default is None.
        :type left_index: Optional[str], optional
        :right_index: The DataFrame column name to use to match rows
            to nodes. If not provided, the DataFrame's index is used. Default is None.
        :type right_index: Optional[str], optional

        :returns: None
        """
        if right_index is not None:
            df = dataframe.set_index(right_index)
        else:
            df = dataframe

        if columns is not None:
            df = df[columns]

        check_dataframe(df)

        column_dictionaries = df.to_dict()

        if left_index is not None:
            ids_to_index = networkx.get_node_attributes(self, left_index)
        else:
            # When the left_index is node ID, the matching is just
            # a redundant {node: node} dictionary
            ids_to_index = dict(zip(self.nodes, self.nodes))

        node_attributes = {
            node_id: {
                column: values[index] for column, values in column_dictionaries.items()
            }
            for node_id, index in ids_to_index.items()
        }

        networkx.set_node_attributes(self, node_attributes)

    @property
    def islands(self) -> Set:
        """
        :returns: The set of degree-0 nodes.
        :rtype: Set
        """
        return set(node for node in self if self.degree[node] == 0)

    def warn_for_islands(self) -> None:
        """
        :returns: None

        :raises: UserWarning if the graph has any islands (degree-0 nodes).
        """
        islands = self.islands
        if len(self.islands) > 0:
            warnings.warn(
                "Found islands (degree-0 nodes). Indices of islands: {}".format(islands)
            )

    def issue_warnings(self) -> None:
        """
        :returns: None

        :raises: UserWarning if the graph has any red flags (right now, only islands).
        """
        self.warn_for_islands()


def add_boundary_perimeters(graph: Graph, geometries: pd.Series) -> None:
    """
    Add shared perimeter between nodes and the total geometry boundary.

    :param graph: NetworkX graph
    :type graph: :class:`Graph`
    :param geometries: :class:`geopandas.GeoSeries` containing geometry information.
    :type geometries: :class:`pandas.Series`

    :returns: The updated graph.
    :rtype: Graph
    """
    from shapely.ops import unary_union
    from shapely.prepared import prep

    prepared_boundary = prep(unary_union(geometries).boundary)

    boundary_nodes = geometries.boundary.apply(prepared_boundary.intersects)

    for node in graph:
        graph.nodes[node]["boundary_node"] = bool(boundary_nodes[node])
        if boundary_nodes[node]:
            total_perimeter = geometries[node].boundary.length
            shared_perimeter = sum(
                neighbor_data["shared_perim"] for neighbor_data in graph[node].values()
            )
            boundary_perimeter = total_perimeter - shared_perimeter
            graph.nodes[node]["boundary_perim"] = boundary_perimeter


def check_dataframe(df: pd.DataFrame) -> None:
    """
    :returns: None

    :raises: UserWarning if the dataframe has any NA values.
    """
    for column in df.columns:
        if sum(df[column].isna()) > 0:
            warnings.warn("NA values found in column {}!".format(column))


def remove_geometries(data: networkx.Graph) -> None:
    """
    Remove geometry attributes from NetworkX adjacency data object,
    because they are not serializable. Mutates the ``data`` object.

    Does nothing if no geometry attributes are found.

    :param data: an adjacency data object (returned by
        :func:`networkx.readwrite.json_graph.adjacency_data`)
    :type data: networkx.Graph

    :returns: None
    """
    for node in data["nodes"]:
        bad_keys = []
        for key in node:
            # having a ``__geo_interface__``` property identifies the object
            # as being a ``shapely`` geometry object
            if hasattr(node[key], "__geo_interface__"):
                bad_keys.append(key)
        for key in bad_keys:
            del node[key]


def convert_geometries_to_geojson(data: networkx.Graph) -> None:
    """
    Convert geometry attributes in a NetworkX adjacency data object
    to GeoJSON, so that they can be serialized. Mutates the ``data`` object.

    Does nothing if no geometry attributes are found.

    :param data: an adjacency data object (returned by
        :func:`networkx.readwrite.json_graph.adjacency_data`)
    :type data: networkx.Graph

    :returns: None
    """
    for node in data["nodes"]:
        for key in node:
            # having a ``__geo_interface__``` property identifies the object
            # as being a ``shapely`` geometry object
            if hasattr(node[key], "__geo_interface__"):
                # The ``__geo_interface__`` property is essentially GeoJSON.
                # This is what :func:`geopandas.GeoSeries.to_json` uses under
                # the hood.
                node[key] = node[key].__geo_interface__


class FrozenGraph:
    """
    Represents an immutable graph to be partitioned. It is based off :class:`Graph`.

    This speeds up chain runs and prevents having to deal with cache invalidation issues.
    This class behaves slightly differently than :class:`Graph` or :class:`networkx.Graph`.

    Not intended to be a part of the public API.

    :ivar graph: The underlying graph.
    :type graph: Graph
    :ivar size: The number of nodes in the graph.
    :type size: int

    Note
    ----
    The class uses `__slots__` for improved memory efficiency.
    """

    __slots__ = ["graph", "size"]

    def __init__(self, graph: Graph) -> None:
        """
        Initialize a FrozenGraph from a Graph.

        :param graph: The mutable Graph to be converted into an immutable graph
        :type graph: Graph

        :returns: None
        """
        self.graph = networkx.classes.function.freeze(graph)
        self.graph.join = frozen
        self.graph.add_data = frozen

        self.size = len(self.graph)

    def __len__(self) -> int:
        return self.size

    def __getattribute__(self, __name: str) -> Any:
        try:
            return object.__getattribute__(self, __name)
        except AttributeError:
            return object.__getattribute__(self.graph, __name)

    def __getitem__(self, __name: str) -> Any:
        return self.graph[__name]

    def __iter__(self) -> Iterable[Any]:
        yield from self.node_indices

    @functools.lru_cache(16384)
    def neighbors(self, n: Any) -> Tuple[Any, ...]:
        return tuple(self.graph.neighbors(n))

    @functools.cached_property
    def node_indices(self) -> Iterable[Any]:
        return self.graph.node_indices

    @functools.cached_property
    def edge_indices(self) -> Iterable[Any]:
        return self.graph.edge_indices

    @functools.lru_cache(16384)
    def degree(self, n: Any) -> int:
        return self.graph.degree(n)

    @functools.lru_cache(65536)
    def lookup(self, node: Any, field: str) -> Any:
        return self.graph.nodes[node][field]

    def subgraph(self, nodes: Iterable[Any]) -> "FrozenGraph":
        return FrozenGraph(self.graph.subgraph(nodes))
