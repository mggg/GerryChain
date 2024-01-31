"""
This module provides a Grid class used for creating and manipulating grid partitions.
It's part of the GerryChain suite, designed to facilitate experiments with redistricting
plans without the need for extensive data processing. This module relies on NetworkX for
graph operations and integrates with GerryChain's Partition class.

Dependencies:

- math: For math.floor() function.
- networkx: For graph operations with using the graph structure in
    :class:`~gerrychain.graph.Graph`.
- typing: Used for type hints.
"""

import math
import networkx
from gerrychain.partition import Partition
from gerrychain.graph import Graph
from gerrychain.updaters import (
    Tally,
    boundary_nodes,
    cut_edges,
    cut_edges_by_part,
    exterior_boundaries,
    interior_boundaries,
    perimeter,
)
from gerrychain.metrics import polsby_popper
from typing import Callable, Dict, Optional, Tuple, Any


class Grid(Partition):
    """
    The :class:`Grid` class represents a grid partitioned into districts.
    It is useful for running little experiments with GerryChain without needing to do
    any data processing or cleaning to get started.

    Example usage::

        grid = Grid((10,10))

    The nodes of ``grid.graph`` are labelled by tuples ``(i,j)``, for ``0 <= i <= 10``
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
        dimensions: Optional[Tuple[int, int]] = None,
        with_diagonals: bool = False,
        assignment: Optional[Dict] = None,
        updaters: Optional[Dict[str, Callable]] = None,
        parent: Optional["Grid"] = None,
        flips: Optional[Dict[Tuple[int, int], int]] = None,
    ) -> None:
        """
        If the updaters are not specified, the default updaters are used, which are as follows::

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


        :param dimensions: The grid dimensions (rows, columns), defaults to None.
        :type dimensions: Tuple[int, int], optional
        :param with_diagonals: If True, includes diagonal connections, defaults to False.
        :type with_diagonals: bool, optional
        :param assignment: Node-to-district assignments, defaults to None.
        :type assignment: Dict, optional
        :param updaters: Custom updater functions, defaults to None.
        :type updaters: Dict[str, Callable], optional
        :param parent: Parent Grid object for inheritance, defaults to None.
        :type parent: Grid, optional
        :param flips: Node flips for partition changes, defaults to None.
        :type flips: Dict[Tuple[int, int], int], optional

        :raises Exception: If neither dimensions nor parent is provided.
        """
        if dimensions:
            self.dimensions = dimensions
            graph = Graph.from_networkx(create_grid_graph(dimensions, with_diagonals))

            if not assignment:
                thresholds = tuple(math.floor(n / 2) for n in self.dimensions)
                assignment = {
                    node: color_quadrants(node, thresholds) for node in graph.nodes  # type: ignore
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

    def __str__(self):
        rows = self.as_list_of_lists()
        return "\n".join(["".join([str(x) for x in row]) for row in rows]) + "\n"

    def __repr__(self):
        dims = "x".join(str(d) for d in self.dimensions)
        number_of_parts = len(self.parts)
        s = "s" if number_of_parts > 1 else ""
        return "{} Grid\nPartitioned into {} part{}".format(dims, number_of_parts, s)

    def as_list_of_lists(self):
        """
        Returns the grid as a list of lists (like a matrix), where the (i,j)th
        entry is the assigned district of the node in position (i,j) on the
        grid.

        :returns: List of lists representing the grid.
        :rtype: List[List[int]]
        """
        m, n = self.dimensions
        return [[self.assignment.mapping[(i, j)] for i in range(m)] for j in range(n)]


def create_grid_graph(dimensions: Tuple[int, int], with_diagonals: bool) -> Graph:
    """
    Creates a grid graph with the specified dimensions.
    Optionally includes diagonal connections between nodes.

    :param dimensions: The grid dimensions (rows, columns).
    :type dimensions: Tuple[int, int]
    :param with_diagonals: If True, includes diagonal connections.
    :type with_diagonals: bool

    :returns: A grid graph.
    :rtype: Graph

    :raises ValueError: If the dimensions are not a tuple of length 2.
    """
    if len(dimensions) != 2:
        raise ValueError("Expected two dimensions.")
    m, n = dimensions
    graph = networkx.generators.lattice.grid_2d_graph(m, n)

    networkx.set_edge_attributes(graph, 1, "shared_perim")

    if with_diagonals:
        nw_to_se = [
            ((i, j), (i + 1, j + 1)) for i in range(m - 1) for j in range(n - 1)
        ]
        sw_to_ne = [
            ((i, j + 1), (i + 1, j)) for i in range(m - 1) for j in range(n - 1)
        ]
        diagonal_edges = nw_to_se + sw_to_ne
        graph.add_edges_from(diagonal_edges)
        for edge in diagonal_edges:
            graph.edges[edge]["shared_perim"] = 0

    networkx.set_node_attributes(graph, 1, "population")
    networkx.set_node_attributes(graph, 1, "area")

    tag_boundary_nodes(graph, dimensions)

    return graph


def give_constant_attribute(graph: Graph, attribute: Any, value: Any) -> None:
    """
    Sets the specified attribute to the specified value for all nodes in the graph.

    :param graph: The graph to modify.
    :type graph: Graph
    :param attribute: The attribute to set.
    :type attribute: Any
    :param value: The value to set the attribute to.
    :type value: Any

    :returns: None
    """
    for node in graph.nodes:
        graph.nodes[node][attribute] = value


def tag_boundary_nodes(graph: Graph, dimensions: Tuple[int, int]) -> None:
    """
    Adds the boolean attribute ``boundary_node`` to each node in the graph.
    If the node is on the boundary of the grid, that node also gets the attribute
    ``boundary_perim`` which is determined by the function :func:`get_boundary_perim`.

    :param graph: The graph to modify.
    :type graph: Graph
    :param dimensions: The dimensions of the grid.
    :type dimensions: Tuple[int, int]

    :returns: None
    """
    m, n = dimensions
    for node in graph.nodes:
        if node[0] in [0, m - 1] or node[1] in [0, n - 1]:
            graph.nodes[node]["boundary_node"] = True
            graph.nodes[node]["boundary_perim"] = get_boundary_perim(node, dimensions)
        else:
            graph.nodes[node]["boundary_node"] = False


def get_boundary_perim(node: Tuple[int, int], dimensions: Tuple[int, int]) -> int:
    """
    Determines the boundary perimeter of a node on the grid.
    The boundary perimeter is the number of sides of the node that
    are on the boundary of the grid.

    :param node: The node to check.
    :type node: Tuple[int, int]
    :param dimensions: The dimensions of the grid.
    :type dimensions: Tuple[int, int]

    :returns: The boundary perimeter of the node.
    :rtype: int
    """
    m, n = dimensions
    if node in [(0, 0), (m - 1, 0), (0, n - 1), (m - 1, n - 1)]:
        return 2
    elif node[0] in [0, m - 1] or node[1] in [0, n - 1]:
        return 1
    else:
        return 0


def color_half(node: Tuple[int, int], threshold: int) -> int:
    """
    Assigns a color (as an integer) to a node based on its x-coordinate.

    This function is used to partition the grid into two parts based on a given threshold.
    Nodes with an x-coordinate less than or equal to the threshold are assigned one color,
    and nodes with an x-coordinate greater than the threshold are assigned another.

    :param node: The node to color, represented as a tuple of coordinates (x, y).
    :type node: Tuple[int, int]
    :param threshold: The x-coordinate value that determines the color assignment.
    :type threshold: int

    :returns: An integer representing the color of the node. Returns 0 for nodes with
        x-coordinate less than or equal to the threshold, and 1 otherwise.
    :rtype: int
    """
    x = node[0]
    return 0 if x <= threshold else 1


def color_quadrants(node: Tuple[int, int], thresholds: Tuple[int, int]) -> int:
    """
    Assigns a color (as an integer) to a node based on its position relative to
    specified threshold coordinates, effectively dividing the grid into four quadrants.

    The function uses two threshold values (one for each axis) to determine the color.
    Each combination of being higher or lower than the threshold on each axis results
    in a different color.

    :param node: The node to color, represented as a tuple of coordinates (x, y).
    :type node: Tuple[int, int]
    :param thresholds: A tuple of two integers representing the threshold coordinates
        (x_threshold, y_threshold).
    :type thresholds: Tuple[int, int]

    :returns: An integer representing the color of the node, determined by its quadrant.
    :rtype: int
    """
    x, y = node
    x_color = 0 if x < thresholds[0] else 1
    y_color = 0 if y < thresholds[1] else 2
    return x_color + y_color
