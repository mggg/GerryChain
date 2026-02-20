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
from typing import Any, Callable, Dict, Optional, Tuple

import networkx

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
    The :class:`Grid` class is a subclass of Partition.  It represents a grid graph
    with some node data and some edge data and that has been partitioned into
    districts (parts).  It is a quick way to get a Partition that you can then
    experiment with.

    It is useful for running little experiments with GerryChain without needing to do
    any data processing or cleaning to get started.

    In a real GerryChain task, one would typically need to find data, clean that data
    (for instance to get rid of islands), make sure that the data you wanted
    for your analysis exists for every node (for instance, population), and then
    create an initial assignment of nodes to districts (parts).  The :class:`Grid`
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
            Note that flips are a dict of the form: {node_id: part}.  In the case
            of a Grid, a node_id is a tuple indicating its position in the grid,
            so for a Grid the flips look like: {(row_node_id, col_node_id): part}
        :type flips: Dict[Tuple[int, int], int], optional

        :raises Exception: If neither dimensions nor parent is provided.
        """

        # Note that Grid graphs have node_ids that are tuples not integers.

        if dimensions:
            self.dimensions = dimensions
            graph = _create_grid_nx_graph(dimensions, with_diagonals)

            if not assignment:
                thresholds = tuple(math.floor(n / 2) for n in self.dimensions)
                assignment = {
                    node_id: _color_quadrants(node_id, thresholds)  # type: ignore
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

    def __str__(self):
        rows = self._as_list_of_lists()
        return "\n".join(["".join([str(x) for x in row]) for row in rows]) + "\n"

    def __repr__(self):
        dims = "x".join(str(d) for d in self.dimensions)
        number_of_parts = len(self.parts)
        s = "s" if number_of_parts > 1 else ""
        return "{} Grid\nPartitioned into {} part{}".format(dims, number_of_parts, s)

    def _as_list_of_lists(self):
        """
        Returns the grid as a list of lists (like a matrix), where the (i,j)th
        entry is the assigned district of the node in position (i,j) on the
        grid.

        :returns: List of lists representing the grid.
        :rtype: List[List[int]]
        """
        m, n = self.dimensions
        return [[self.assignment.mapping[(i, j)] for i in range(m)] for j in range(n)]


def _create_grid_nx_graph(dimensions: Tuple[int, ...], with_diagonals: bool) -> Graph:
    """
    Creates a grid graph with the specified dimensions.
    Optionally includes diagonal connections (edges) between nodes.

    It sets the following data on nodes and edges:

    Node Data:

    * "population" set to 1,
    * "area" set to 1
    * "boundary_node" set to True iff a boundary node - see _get_boundary_perim()
    * "boundary_perim" set to perimeter touching the boundary - see _get_boundary_perim()

    Edge Data:

    * "shared_perim" set to 1 except for diagonal edges (if any)

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
    nx_graph = networkx.generators.lattice.grid_2d_graph(m, n)

    # In a grid graph the shared perimeter with every other node is 1
    networkx.set_edge_attributes(nx_graph, 1, "shared_perim")

    # if "with_diagonals" then create edges between nodes on diagonals
    if with_diagonals:
        nw_to_se = [((i, j), (i + 1, j + 1)) for i in range(m - 1) for j in range(n - 1)]
        sw_to_ne = [((i, j + 1), (i + 1, j)) for i in range(m - 1) for j in range(n - 1)]
        diagonal_edges = nw_to_se + sw_to_ne
        nx_graph.add_edges_from(diagonal_edges)
        for edge in diagonal_edges:
            # diagonals meet at a point, hence shared perimeter is zero
            nx_graph.edges[edge]["shared_perim"] = 0

    networkx.set_node_attributes(nx_graph, 1, "population")
    networkx.set_node_attributes(nx_graph, 1, "area")

    _tag_boundary_nodes(nx_graph, dimensions)

    return Graph.from_networkx(nx_graph)


# frm: TODO: Refactoring: give_constant_attribute() is never used - delete it?
#
# This routine is never used in GerryChain code, and its implementation is
# trivial, so I am inclined to delete it - but perhaps it is used in legacy code?
#
# If we keep it, however, it should be moved to graph.py as it is a general purpose
# graph utility not a Grid related function.
#
# Peter said (January 2026): Nah, let's get rid of it...


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
    for node_id in graph.node_indices:
        graph.node_data(node_id)[attribute] = value


def _tag_boundary_nodes(nx_graph: networkx.Graph, dimensions: Tuple[int, int]) -> None:
    """
    Adds the boolean attribute ``boundary_node`` to each node in the graph.
    If the node is on the boundary of the grid, that node also gets the attribute
    ``boundary_perim`` which is determined by the function :func:`_get_boundary_perim`.

    :param graph: The graph to modify.
    :type graph: Graph
    :param dimensions: The dimensions of the grid.
    :type dimensions: Tuple[int, int]

    :returns: None
    """

    # Note that in the code below, a node_id is a tuple indicating its position
    # in the grid (row, col), so that node_id[0] denotes the row for a node and
    # node_id[1] indicates the column.  The code just tests to see if a node's
    # row or column is on the boundary - meaning it is either 0 or the max value
    # of a row or col.

    m, n = dimensions
    for node_id in nx_graph.nodes:
        if node_id[0] in [0, m - 1] or node_id[1] in [0, n - 1]:
            nx_graph.nodes[node_id]["boundary_node"] = True
            nx_graph.nodes[node_id]["boundary_perim"] = _get_boundary_perim(node_id, dimensions)
        else:
            nx_graph.nodes[node_id]["boundary_node"] = False


def _get_boundary_perim(node_id: Tuple[int, int], dimensions: Tuple[int, int]) -> int:
    """
    Determines the boundary perimeter of a node on the grid.
    The boundary perimeter is the number of sides of the node that
    are on the boundary of the grid.

    :param node_id: The ID of the node to check.  Note that the node_id is
        a tuple of the form (row, col) so that node_id[0] denotes the row
        a node is in and node_id[1] denotes its column.
    :type node_id: Tuple[int, int]
    :param dimensions: The dimensions of the grid.
    :type dimensions: Tuple[int, int]

    :returns: The boundary perimeter of the node.
    :rtype: int
    """
    m, n = dimensions
    if node_id in [(0, 0), (m - 1, 0), (0, n - 1), (m - 1, n - 1)]:
        return 2
    elif node_id[0] in [0, m - 1] or node_id[1] in [0, n - 1]:
        return 1
    else:
        return 0


# frm: TODO: Refactoring:  color_half() is never used anywhere in GerryChain code.  Delete it?
#
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


def _color_quadrants(node: Tuple[int, int], thresholds: Tuple[int, int]) -> int:
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
