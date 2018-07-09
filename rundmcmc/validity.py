import collections
import random

import networkx as nx
import networkx.algorithms.shortest_paths.weighted as nx_path
from networkx import NetworkXNoPath

from rundmcmc.updaters import CountySplit


def L1_reciprocal_polsby_popper(partition):
    return sum(1 / value for value in partition['polsby_popper'].values())


def L1_reciprocal_discrete_polsby_popper(partition):
    return sum(1 / value for value in partition['discrete_polsby_popper'].values())


def population(partition):
    return partition['population'].values()


def within_percent_of_ideal_population(initial_partition, percent=0.01):
    """
    Slightly different implementation of the 'within 1%' rule, based on the text of
    Moon's PA report.
    """
    number_of_districts = len(initial_partition['population'].keys())
    total_population = sum(initial_partition['population'].values())
    ideal_population = total_population / number_of_districts
    bounds = ((1 - percent) * ideal_population, (1 + percent) * ideal_population)
    return Bounds(func=population, bounds=bounds)


class Bounds:
    def __init__(self, func, bounds):
        self.func = func
        self.bounds = bounds

    def __call__(self, *args, **kwargs):
        lower, upper = self.bounds
        values = self.func(*args, **kwargs)
        return lower <= min(values) and max(values) <= upper


class UpperBound:
    def __init__(self, func, bound):
        self.func = func
        self.bound = bound

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs) <= self.bound


class LowerBound:
    def __init__(self, func, bound):
        self.func = func
        self.bound = bound

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs) >= self.bound


class Validator:
    def __init__(self, constraints):
        """:constraints: List of validator functions that will check partitions."""
        self.constraints = constraints

    def __call__(self, partition):
        """:partition: :class:`Partition` class to check."""

        # check each constraint function and fail when a constraint test fails
        for constraint in self.constraints:
            if constraint(partition) is False:
                return False

        # all constraints are satisfied
        return True


def single_flip_contiguous(partition):
    """
    Check if swapping the given node from its old assignment disconnects the
    old assignment class.

    :parition: Current :class:`.Partition` object.

    :flips: Dictionary of proposed flips, with `(nodeid: new_assignment)`
            pairs. If `flips` is `None`, then fallback to the
            :func:`.contiguous` check.

    :returns: True if contiguous, and False otherwise.

    We assume that `removed_node` belonged to an assignment class that formed a
    connected subgraph. To see if its removal left the subgraph connected, we
    check that the neighbors of the removed node are still connected through
    the changed graph.

    """
    parent = partition.parent
    flips = partition.flips
    if not flips or not parent:
        return contiguous(partition)

    graph = partition.graph
    assignment_dict = parent.assignment

    def proposed_assignment(node):
        """Return the proposed assignment of the given node."""
        if node in flips:
            return flips[node]

        return assignment_dict[node]

    def partition_edge_weight(start_node, end_node, edge_attrs):
        """
        Compute the district edge weight, which is 1 if the nodes have the same
        assignment, and infinity otherwise.
        """
        if proposed_assignment(start_node) != proposed_assignment(end_node):
            return float("inf")

        return 1

    for changed_node, _ in flips.items():
        old_neighbors = []
        old_assignment = assignment_dict[changed_node]

        for node in graph.neighbors(changed_node):
            if proposed_assignment(node) == old_assignment:
                old_neighbors.append(node)

        if not old_neighbors:
            # Under our assumptions, if there are no old neighbors, then the
            # old_assignment district has vanished. It is trivially connected.
            return True

        start_neighbor = random.choice(old_neighbors)

        for neighbor in old_neighbors:
            try:
                distance, _ = nx_path.single_source_dijkstra(graph, start_neighbor, neighbor,
                                                             weight=partition_edge_weight)
                if not (distance < float("inf")):
                    return False
            except NetworkXNoPath:
                return False

    # All neighbors of all changed nodes are connected, so the new graph is
    # connected.
    return True


def contiguous(partition):
    """
    :parition: Current :class:`.Partition` object.
    :flips: Dictionary of proposed flips, with `(nodeid: new_assignment)`
            pairs. If `flips` is `None`, then fallback to the
            :func:`.contiguous` check.

    :returns: True if contiguous, False otherwise.
    """
    flips = partition.flips
    if not flips:
        flips = dict()

    def proposed_assignment(node):
        """Return the proposed assignment of the given node."""
        return partition.assignment[node]
    # TODO

    # Creates a dictionary where the key is the district and the value is
    # a list of VTDs that belong to that district
    district_dict = {}
    # TODO
    for node in partition.graph.nodes:
        # TODO
        dist = proposed_assignment(node)
        if dist in district_dict:
            district_dict[dist].append(node)
        else:
            district_dict[dist] = [node]

    # Checks if the subgraph of all districts are connected(contiguous)
    for key in district_dict:
        # TODO
        tmp = partition.graph.subgraph(district_dict[key])
        if nx.is_connected(tmp) is False:
            return False

    return True


def fast_connected(partition):
    """
        Checks that a given partition's components are connected using
        a simple breadth-first search.
        :partition: Instance of Partition; contains connected components.
        :flips: Dictionary of proposed flips.
        :return: Boolean; Are the components of this partition connected?
    """
    assignment = partition.assignment

    # Inverts the assignment dictionary so that lists of VTDs are keyed
    # by their congressional districts.
    districts = collections.defaultdict(set)

    for vtd in assignment:
        districts[assignment[vtd]].add(vtd)

    # Generates a subgraph for each district and perform a BFS on it
    # to check connectedness.
    for district in districts:
        adj = nx.to_dict_of_lists(partition.graph, districts[district])
        if bfs(adj) is False:
            return False

    return True


def bfs(graph):
    """
        Performs a breadth-first search on the provided graph and
        returns true or false depending on whether the graph is
        connected.
        :graph: Dict-of-lists; an adjacency matrix.
        :return: Boolean; is this graph connected?
    """
    q = [next(iter(graph))]
    visited = set()
    total_vertices = len(list(graph.keys()))

    # bfs!
    while len(q) is not 0:
        current = q.pop(0)
        neighbors = graph[current]

        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                q += [neighbor]

    return total_vertices == len(visited)


def fast_local_connected(partition, flips=None):
    """
        Checks that a given partition's components are connected, but
        uses a specific optimized method (with a forthcoming proof).
        :partition: Instance of Partition; contains connected components.
        :flips: Dictionary of proposed flips.
        :return: Boolean; are the components of this partition connected?
    """
    pass


# TODO make attrName and percentage configurable
def districts_within_tolerance(partition, attribute_name="population", percentage=0.1):
    """
    :partition: partition class instance
    :attrName: string that is the name of an updater in partition
    :percentage: what percent difference is allowed
    :return: boolean of if the districts are within specified tolerance
    """
    if percentage >= 1:
        percentage *= 0.01

    values = partition[attribute_name].values()
    max_difference = max(values) - min(values)

    within_tolerance = max_difference <= percentage * min(values)
    return within_tolerance


def refuse_new_splits(partition_county_field):
    """
    Refuse all proposals that split a county that was previous unsplit.

    :partition_county_field: Name of field for county information generated by
                             :func:`.county_splits`.

    """
    def _refuse_new_splits(partition):
        for county_info in partition[partition_county_field].values():
            if county_info.split == CountySplit.NEW_SPLIT:
                return False

        return True

    return _refuse_new_splits


def no_vanishing_districts(partition):
    if not partition.parent:
        return True
    return len(partition) == len(partition.parent)
