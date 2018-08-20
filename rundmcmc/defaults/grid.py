import math

import networkx

from rundmcmc.partition import Partition
from rundmcmc.updaters import (Tally, cut_edges, cut_edges_by_part,
                              perimeters, polsby_popper,
                              exterior_boundaries, interior_boundaries,
                              boundary_nodes)


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
                             'perimeters': perimeters,
                            'exterior_boundaries': exterior_boundaries,
                            'interior_boundaries': interior_boundaries,
                            'boundary_nodes': boundary_nodes,
                            'areas': Tally('area', alias='areas'),
                            'polsby_popper': polsby_popper,
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
        return "{} Grid\nPartitioned into {} part{}".format(dims, number_of_parts, s)

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

    networkx.set_edge_attributes(graph, 1, 'shared_perim')

    if with_diagonals:
        nw_to_se = [((i, j), (i + 1, j + 1)) for i in range(m - 1) for j in range(n - 1)]
        sw_to_ne = [((i, j + 1), (i + 1, j)) for i in range(m - 1) for j in range(n - 1)]
        diagonal_edges = nw_to_se + sw_to_ne
        graph.add_edges_from(diagonal_edges)
        for edge in diagonal_edges:
            graph.edges[edge]['shared_perim'] = 0

    networkx.set_node_attributes(graph, 1, 'population')
    networkx.set_node_attributes(graph, 1, 'area')

    tag_boundary_nodes(graph, dimensions)

    return graph


def give_constant_attribute(graph, attribute, value):
    for node in graph.nodes:
        graph.nodes[node][attribute] = value


def tag_boundary_nodes(graph, dimensions):
    m, n = dimensions
    for node in graph.nodes:
        if node[0] in [0, m - 1] or node[1] in [0, n - 1]:
            graph.nodes[node]['boundary_node'] = True
            graph.nodes[node]['boundary_perim'] = get_boundary_perim(node, dimensions)
        else:
            graph.nodes[node]['boundary_node'] = False


def get_boundary_perim(node, dimensions):
    m, n = dimensions
    if node in [(0, 0), (m - 1, 0), (0, n - 1), (m - 1, n - 1)]:
        return 2
    elif node[0] in [0, m - 1] or node[1] in [0, n - 1]:
        return 1
    else:
        return 0


def color_half(node, threshold=5):
    x = node[0]
    return 0 if x <= threshold else 1


def color_quadrants(node, thresholds):
    x, y = node
    x_color = 0 if x < thresholds[0] else 1
    y_color = 0 if y < thresholds[1] else 2
    return x_color + y_color


def grid_size(parition):
    ''' This is a hardcoded population function
    for the grid class'''

    L = parition.as_list_of_lists()
    permit = [3, 4, 5]

    sizes = [0, 0, 0, 0]

    for i in range(len(L)):
        for j in range(len(L[0])):
            sizes[L[i][j]] += 1

    return all(x in permit for x in sizes)
