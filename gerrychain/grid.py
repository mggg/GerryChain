"""
This module provides a Grid class used for creating and manipulating grid partitions.
It's part of the GerryChain suite, designed to facilitate experiments with redistricting
plans without the need for extensive data processing. This module relies on NetworkX for
graph operations and integrates with GerryChain's Partition class.

Dependencies:

- math: For math.floor() function.
- networkx: For graph operations with using the graph structure in
    Graph.
- typing: Used for type hints.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Hashable
from typing import Any, cast

import networkx
from networkx.generators.lattice import grid_2d_graph

from gerrychain._deprecated import deprecated_alias, legacy_give_constant_attribute
from gerrychain.graph import Graph
from gerrychain.metrics import polsby_popper
from gerrychain.partition import Partition
from gerrychain.updaters import (
    Tally,
    boundary_nodes,
    cut_edges,
    cut_edges_by_part,
    exterior_boundaries,
    interior_boundaries,
    perimeter,
)


class Grid(Partition):
    """
    The Grid class is a subclass of Partition.  It represents a grid graph
    with some node data and some edge data and that has been partitioned into
    districts (parts).  It is a quick way to get a Partition that you can then
    experiment with.

    It is useful for running little experiments with GerryChain without needing to do
    any data processing or cleaning to get started.

    In a real GerryChain task, one would typically need to find data, clean that data
    (for instance to get rid of islands), make sure that the data you wanted
    for your analysis exists for every node (for instance, population), and then
    create an initial assignment of nodes to districts (parts).  The Grid
    class allows you to obtain a Partition object that has all of those tasks
    already done.

    The following node and edge data are set:

    Node Data:

    * "population" set to 1,
    * "area" set to 1
    * "boundary_node" set to True iff a boundary node - see _get_boundary_perim()
    * "boundary_perim" set to perimeter touching the boundary - see _get_boundary_perim()

    Edge Data:

    * "shared_perim" set to 1 except for diagonal edges (if any)

    The number of districts (parts) is set to be half the number of columns (rounded
    down)

    Example usage::

        grid = Grid((10,10))

    Note that the nodes of ``grid.graph`` are labelled by tuples ``(i,j)``, for ``0 <= i <= 10``
    and ``0 <= j <= 10``. Each node has an ``area`` of 1 and each edge has ``shared_perim`` 1.
    """

    default_updaters = {
        "cut_edges": cut_edges,
        "population": Tally("population"),
        "perimeter": perimeter,
        "exterior_boundaries": exterior_boundaries,
        "interior_boundaries": interior_boundaries,
        "boundary_nodes": boundary_nodes,
        "area": Tally("area", alias="area"),
        "polsby_popper": polsby_popper,
        "cut_edges_by_part": cut_edges_by_part,
    }

    def __init__(
        self,
        dimensions: tuple[int, int] | None = None,
        with_diagonals: bool = False,
        assignment: dict[tuple[int, int], int] | None = None,
        updaters: dict[str, Callable[[Partition], object]] | None = None,
        parent: Grid | None = None,
        flips: dict[tuple[int, int], int] | None = None,
    ) -> None:
        """Initialize a Grid instance.

        Args:
            dimensions (tuple[int, int], optional): The grid dimensions (rows, columns), defaults
                to None.
            with_diagonals (bool, optional): If True, includes diagonal connections, defaults to
                False.
            assignment (dict, optional): Node-to-district assignments, defaults to None.
            updaters (dict[str, Callable], optional): Custom updater functions, defaults to None.
            parent (Grid, optional): Parent Grid object for inheritance, defaults to None.
            flips (dict[tuple[int, int], int], optional): Node flips for partition changes,
                defaults to None. Note that flips are a dict of the form: {node_id: part}. In the
                case of a Grid, a node_id is a tuple indicating its position in the grid, so for a
                Grid the flips look like: {(row_node_id, col_node_id): part}

        Raises:
            Exception: If neither dimensions nor parent is provided.
        """

        # Note that Grid graphs have node_ids that are tuples not integers.

        if dimensions:
            self.dimensions = dimensions
            graph = _create_grid_nx_graph(dimensions, with_diagonals)

            if not assignment:
                thresholds = (
                    math.floor(self.dimensions[0] / 2),
                    math.floor(self.dimensions[1] / 2),
                )
                assignment = {
                    cast(tuple[int, int], node_id): _color_quadrants(
                        cast(tuple[int, int], node_id), thresholds
                    )
                    for node_id in graph.node_indices
                }

            if not updaters:
                updaters = dict()
            updaters.update(self.default_updaters)

            super().__init__(graph, assignment, updaters)
        elif parent:
            self.dimensions = parent.dimensions
            super().__init__(parent=parent, flips=flips)
        else:
            raise Exception("Not a good way to create a Partition")

    def __str__(self) -> str:
        rows = self._as_list_of_lists()
        return "\n".join(["".join([str(x) for x in row]) for row in rows]) + "\n"

    def __repr__(self) -> str:
        dims = "x".join(str(d) for d in self.dimensions)
        number_of_parts = len(self.parts)
        s = "s" if number_of_parts > 1 else ""
        return f"{dims} Grid\nPartitioned into {number_of_parts} part{s}"

    def _as_list_of_lists(self) -> list[list[int]]:
        """Return List of lists representing the grid.

        Returns the grid as a list of lists (like a matrix), where the (i,j)th entry is the
        assigned district of the node in position (i,j) on the grid.

        Returns:
            list[list[int]]: List of lists representing the grid.
        """
        m, n = self.dimensions
        return [[cast(int, self.assignment.mapping[(i, j)]) for i in range(m)] for j in range(n)]

    as_list_of_lists = deprecated_alias(
        "Grid.as_list_of_lists",
        "Grid._as_list_of_lists",
        _as_list_of_lists,
    )


def _create_grid_nx_graph(dimensions: tuple[int, ...], with_diagonals: bool) -> Graph:
    """Creates a grid graph with the specified dimensions

    Node Data:

        * "population" set to 1,
        * "area" set to 1
        * "boundary_node" set to True iff a boundary node - see _get_boundary_perim()
        * "boundary_perim" set to perimeter touching the boundary - see _get_boundary_perim()

    Edge Data:

        * "shared_perim" set to 1 except for diagonal edges (if any)

    Args:
        dimensions (tuple[int, int]): The grid dimensions (rows, columns).
        with_diagonals (bool): If True, includes diagonal connections.

    Returns:
        Graph: A grid graph.

    Raises:
        ValueError: If the dimensions are not a tuple of length 2.
    """
    if len(dimensions) != 2:
        raise ValueError("Expected two dimensions.")
    m, n = dimensions
    nx_graph = cast("networkx.Graph[Hashable, dict[str, Any], dict[str, Any]]", grid_2d_graph(m, n))

    # In a grid graph the shared perimeter with every other node is 1
    for edge in nx_graph.edges:
        nx_graph.edges[edge]["shared_perim"] = 1

    # if "with_diagonals" then create edges between nodes on diagonals
    if with_diagonals:
        nw_to_se = [((i, j), (i + 1, j + 1)) for i in range(m - 1) for j in range(n - 1)]
        sw_to_ne = [((i, j + 1), (i + 1, j)) for i in range(m - 1) for j in range(n - 1)]
        diagonal_edges = nw_to_se + sw_to_ne
        nx_graph.add_edges_from(diagonal_edges)
        for edge in diagonal_edges:
            # diagonals meet at a point, hence shared perimeter is zero
            nx_graph.edges[edge]["shared_perim"] = 0

    for node in nx_graph.nodes:
        nx_graph.nodes[node]["population"] = 1
        nx_graph.nodes[node]["area"] = 1

    _tag_boundary_nodes(nx_graph, dimensions)

    return Graph.from_networkx(nx_graph)


def _tag_boundary_nodes(
    nx_graph: networkx.Graph[Hashable, dict[str, Any], dict[str, Any]],
    dimensions: tuple[int, int],
) -> None:
    """Adds the boolean attribute ``boundary_node`` to each node in the graph.

    If the node is on the boundary of the grid, that node also gets the attribute
    ``boundary_perim`` which is determined by the function `_get_boundary_perim`.

    Args:
        nx_graph (networkx.Graph): The graph to modify.
        dimensions (tuple[int, int]): The dimensions of the grid.

    """

    # Note that in the code below, a node_id is a tuple indicating its position
    # in the grid (row, col), so that node_id[0] denotes the row for a node and
    # node_id[1] indicates the column.  The code just tests to see if a node's
    # row or column is on the boundary - meaning it is either 0 or the max value
    # of a row or col.

    m, n = dimensions
    for node_id in nx_graph.nodes:
        grid_node = cast(tuple[int, int], node_id)
        if grid_node[0] in [0, m - 1] or grid_node[1] in [0, n - 1]:
            nx_graph.nodes[node_id]["boundary_node"] = True
            nx_graph.nodes[node_id]["boundary_perim"] = _get_boundary_perim(grid_node, dimensions)
        else:
            nx_graph.nodes[node_id]["boundary_node"] = False


def _get_boundary_perim(node_id: tuple[int, int], dimensions: tuple[int, int]) -> int:
    """Determines the boundary perimeter of a node on the grid.

    Args:
        node_id (tuple[int, int]): The ID of the node to check. Note that the node_id is a tuple of
            the form (row, col) so that node_id[0] denotes the row a node is in and node_id[1]
            denotes its column.
        dimensions (tuple[int, int]): The dimensions of the grid.

    Returns:
        int: The boundary perimeter of the node.
    """
    m, n = dimensions
    if node_id in [(0, 0), (m - 1, 0), (0, n - 1), (m - 1, n - 1)]:
        return 2
    elif node_id[0] in [0, m - 1] or node_id[1] in [0, n - 1]:
        return 1
    else:
        return 0


def color_half(node: tuple[int, int], threshold: int) -> int:
    """Assigns a color (as an integer) to a node based on its x-coordinate.

    This function is used to partition the grid into two parts based on a given threshold. Nodes
    with an x-coordinate less than or equal to the threshold are assigned one color, and nodes with
    an x-coordinate greater than the threshold are assigned another.

    Args:
        node (tuple[int, int]): The node to color, represented as a tuple of coordinates (x, y).
        threshold (int): The x-coordinate value that determines the color assignment.

    Returns:
        int: An integer representing the color of the node. Returns 0 for nodes with x-coordinate
            less than or equal to the threshold, and 1 otherwise.
    """

    # Note that this routine, color_half, is never used in the GerryChain code.  If it is
    # not part of the external API, then it should be deleted.
    x = node[0]
    return 0 if x <= threshold else 1


def _color_quadrants(node: tuple[int, int], thresholds: tuple[int, int]) -> int:
    """Assigns a color (as an integer) to a node based to divide the grid into four quadrants.

    The function uses two threshold values (one for each axis) to determine the color. Each
    combination of being higher or lower than the threshold on each axis results in a different
    color.

    Args:
        node (tuple[int, int]): The node to color, represented as a tuple of coordinates (x, y).
        thresholds (tuple[int, int]): A tuple of two integers representing the threshold
            coordinates (x_threshold, y_threshold).

    Returns:
        int: An integer representing the color of the node, determined by its quadrant.
    """

    x, y = node
    x_color = 0 if x < thresholds[0] else 1
    y_color = 0 if y < thresholds[1] else 2

    return x_color + y_color


create_grid_graph = deprecated_alias(
    "gerrychain.grid.create_grid_graph",
    "_create_grid_nx_graph",
    _create_grid_nx_graph,
)
give_constant_attribute = legacy_give_constant_attribute
tag_boundary_nodes = deprecated_alias(
    "gerrychain.grid.tag_boundary_nodes",
    "_tag_boundary_nodes",
    _tag_boundary_nodes,
)
get_boundary_perim = deprecated_alias(
    "gerrychain.grid.get_boundary_perim",
    "_get_boundary_perim",
    _get_boundary_perim,
)
color_quadrants = deprecated_alias(
    "gerrychain.grid.color_quadrants",
    "_color_quadrants",
    _color_quadrants,
)
