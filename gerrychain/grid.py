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
# frm TODO:     Decide whether to leave grid.py as-is, at least for now.
#               While it imports NetworkX, it eventually creates a new
#               Graph object which is added to a Partition which will
#               eventually "freeze" and convert the new Graph object to
#               be based on RX (under the covers).
#
#               So, this can be thought of as legacy code that works just
#               fine.  In the future if we want to go full RX everywhere
#               we can decide what to do.
#
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
        # frm: ???: TODO:  This code indicates that flips are a dict of tuple: int which would be
        #                   correct for edge flips, but not for node flips.  Need to check again
        #                   to see if this is correct.  Note that flips is used in the constructor
        #                   so it should fall through to Partition._from_parent()...
        #
        #                   OK - I think that this is a bug.  Parition._from_parent() assumes 
        #                   that flips are a mapping from node to partition not tuple/edge to partition.
        #                   I checked ALL of the code and the constructor for Grid is never passed in
        #                   a flips parameter, so there is no example to check / verify, but it sure
        #                   looks and smells like a bug.  
        #
        #                   The fix would be to just change Dict[Tuple[int, int], int] to be
        #                   Dict[int, int]
        #
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


# frm ???:  Is this intended to be callable / useful for external users?
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
            # frm: TODO:  When/if grid.py is converted to operate on GerryChain Graph
            #               objects instead of NX.Graph objects, this use of NX
            #               EdgeView to get/set edge data will need to change to use
            #               gerrychain_graph.get_edge_data_dict()
            #               
            #               We will also need to think about edge vs edge_id.  In this
            #               case we want an edge_id, so that means we need to look at
            #               how diagonal_edges are created - but that is for the future...
            graph.edges[edge]["shared_perim"] = 0

    # frm: These just set all nodes/edges in the graph to have the given attributes with a value of 1
    networkx.set_node_attributes(graph, 1, "population")
    networkx.set_node_attributes(graph, 1, "area")

    tag_boundary_nodes(graph, dimensions)

    return graph


# frm ???:  Why is this here instead of in graph.py?  Who is it intended for?  Internal vs. External?
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
        # frm original code: graph.nodes[node][attribute] = value
        graph.get_node_data_dict(node)[attribute] = value


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
    #
    # frm: Another case of code that is not clear (at least to me).  It took me
    #       a while to figure out that the name/label for a node in a grid graph
    #       is a tuple and not just a number or string.  The tuple indicates its
    #       position in the grid (x,y) cartesian coordinates, so node[0] below
    #       means its x-position and node[1] means its y-position.  So the if-stmt
    #       below tests whether a node is all the way on the left or the right or 
    #       all the way on the top or the bottom.  If so, it is tagged as a
    #       boundary node and it gets its boundary_perim value set - still not
    #       sure what that does/means...
    # 

    # frm: TODO:  When/if grid.py converts to operating on new GerryChain Graph
    #               objects, all of the graph.nodes[node]... calls should 
    #               be changed to use graph.get_node_data_dict(node)...

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
