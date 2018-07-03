import math

import networkx

from rundmcmc.partition import Partition
from rundmcmc.updaters import Tally, cut_edges, cut_edges_by_part


class Grid(Partition):
    """
    Grid represents a grid partitioned into districts. It is useful for running
    little experiments with the MarkovChain.

    Example usage: `grid = Grid((10,10))`
    """

    def __init__(self, dimensions=None, with_diagonals=False, assignment=None,
                 updaters=None, parent=None, flips=None):
        """
        :dimensions: tuple (m,n) of the desired dimensions of the grid.
        :with_diagonals: (optional, defaults to False) whether to include diagonals
        as edges of the graph (i.e., whether to use 'queen' adjacency rather than
        'rook' adjacency).
        :assignment: (optional) dict matching nodes to their districts. If not
        provided, partitions the grid into 4 quarters of roughly equal size.
        :updaters: (optional) dict matching names of attributes of the Partition
        to functions that compute their values. If not provided, the Grid
        configures the cut_edges updater for convenience.
        """
        if dimensions:
            self.dimensions = dimensions
            graph = create_grid_graph(dimensions, with_diagonals)

            if not assignment:
                thresholds = tuple(math.floor(n / 2) for n in self.dimensions)
                assignment = {node: color_quadrants(node, thresholds) for node in graph.nodes}

            if not updaters:
                updaters = {'cut_edges': cut_edges,
                            'population': Tally('population'),
                            'cut_edges_by_part': cut_edges_by_part}

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
        return f"{dims} Grid\nPartitioned into {str(number_of_parts)} part{s}"

    def as_list_of_lists(self):
        """
        Returns the grid as a list of lists (like a matrix), where the (i,j)th
        entry is the assigned district of the node in position (i,j) on the
        grid.
        """
        m, n = self.dimensions
        return [[self.assignment[(i, j)] for i in range(m)] for j in range(n)]


def create_grid_graph(dimensions, with_diagonals):
    if len(dimensions) != 2:
        raise ValueError("Expected two dimensions.")
    m, n = dimensions
    graph = networkx.generators.lattice.grid_2d_graph(m, n)

    if with_diagonals:
        nw_to_se = [((i, j), (i + 1, j + 1)) for i in range(m - 1) for j in range(n - 1)]
        sw_to_ne = [((i, j + 1), (i + 1, j)) for i in range(m - 1) for j in range(n - 1)]
        diagonal_edges = nw_to_se + sw_to_ne
        graph.add_edges_from(diagonal_edges)

    give_constant_attribute(graph, 'population', 1)
    tag_boundary_nodes(graph, dimensions)

    return graph


def give_constant_attribute(graph, attribute, value):
    for node in graph.nodes:
        graph.nodes[node][attribute] = value


def tag_boundary_nodes(graph, dimensions):
    m, n = dimensions
    for node in graph.nodes:
        graph.nodes[node]['boundary_node'] = node[0] in [0, m - 1] or node[1] in [0, n - 1]


def color_half(node, threshold=5):
    x = node[0]
    return 0 if x <= threshold else 1


def color_quadrants(node, thresholds):
    x, y = node
    x_color = 0 if x < thresholds[0] else 1
    y_color = 0 if y < thresholds[1] else 2
    return x_color + y_color
