import collections
import logging
import random
import math

from heapq import heappush, heappop
from itertools import count

import networkx as nx
import matplotlib.pyplot as plt

from rundmcmc.updaters import CountySplit
from rundmcmc.validity.bounds import (SelfConfiguringLowerBound, SelfConfiguringUpperBound,
                                      Bounds)

logger = logging.getLogger(__name__)


class Validator:
    """
    Collection of validity checks passed to
    :class:`rundmcmc.chain.MarkovChain`.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if all validators pass, and ``False`` if any one fails.

    """

    def __init__(self, constraints):
        """:constraints: List of validator functions that will check partitions."""
        self.constraints = constraints

    def __call__(self, partition):
        """Determine if the given partition is valid.

        :partition: :class:`Partition` class to check.

        """
        # check each constraint function and fail when a constraint test fails
        for constraint in self.constraints:
            is_valid = constraint(partition)
            if is_valid is False:
                return False
            elif is_valid is True:
                pass
            else:
                raise TypeError(f"Constraint {constraint.__name__} returned a non-boolean.")

        # all constraints are satisfied
        return True


def L1_reciprocal_polsby_popper(partition):
    return sum(1 / value for value in partition['polsby_popper'].values())


def L1_polsby_popper(partition):
    return sum(value for value in partition['polsby_popper'].values())


def L2_polsby_popper(partition):
    return math.sqrt(sum(value**2 for value in partition['polsby_popper'].values()))


def L_minus_1_polsby_popper(partition):
    return len(partition.parts) / sum(1 / value for value in partition['polsby_popper'].values())


no_worse_L_minus_1_polsby_popper = SelfConfiguringLowerBound(L_minus_1_polsby_popper)

no_worse_L1_reciprocal_polsby_popper = SelfConfiguringUpperBound(L1_reciprocal_polsby_popper)


def within_percent_of_ideal_population(initial_partition, percent=0.01):
    """
    Require that all districts are within a certain percent of "ideal" (i.e.,
    uniform) population.

    Ideal population is defined as "total population / number of districts."

    :initial_partition: Starting partition from which to compute district information.
    :percent: Allowed percentage deviation.
    :returns: A :class:`.Bounds` instance.

    """
    def population(partition):
        return partition["population"].values()

    number_of_districts = len(initial_partition['population'].keys())
    total_population = sum(initial_partition['population'].values())
    ideal_population = total_population / number_of_districts
    bounds = ((1 - percent) * ideal_population, (1 + percent) * ideal_population)

    return Bounds(population, bounds=bounds)


def are_reachable(G, source, avoid, targets):
    """Check that source can reach targets while avoiding given edges.

    :G: NetworkX graph.

    :source: Starting node.

    :weight: Function with (u, v, data) input that returns that edges weight.

    :targets: Nodes required to find.

    :returns:
    -------
    distance : dictionary
        A mapping from node to shortest distance to that node from one
        of the source nodes.

    This function is a modified form of NetworkX's `_dijkstra_multisource()`.

    """
    G_succ = G._succ if G.is_directed() else G._adj

    push = heappush
    pop = heappop
    dist = {}  # dictionary of final distances
    seen = {}
    # fringe is heapq with 3-tuples (distance,c,node)
    # use the count c to avoid comparing nodes (may not be able to)
    c = count()
    fringe = []

    seen[source] = 0
    push(fringe, (0, next(c), source))

    while not all(t in seen for t in targets) and fringe:
        (d, _, v) = pop(fringe)
        if v in dist:
            continue  # already searched this node.
        dist[v] = d
        for u, e in G_succ[v].items():
            if avoid(v, u, e):
                continue

            vu_dist = dist[v] + 1
            if u not in seen or vu_dist < seen[u]:
                seen[u] = vu_dist
                push(fringe, (vu_dist, next(c), u))

    return all(t in seen for t in targets)


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
    assignment = partition.assignment

    def partition_edge_avoid(start_node, end_node, edge_attrs):
        """
        Compute the district edge weight, which is 1 if the nodes have the same
        assignment, and infinity otherwise.
        """
        if assignment[start_node] != assignment[end_node]:
            # Fun fact: networkx actually refuses to take edges with None
            # weight.
            return True

        return False

    for changed_node, _ in flips.items():
        old_assignment = partition.parent.assignment[changed_node]

        old_neighbors = [node for node in graph.neighbors(changed_node)
                         if assignment[node] == old_assignment]

        if not old_neighbors:
            # Under our assumptions, if there are no old neighbors, then the
            # old_assignment district has vanished. It is trivially connected.
            return True

        start_neighbor = random.choice(old_neighbors)

        connected = are_reachable(graph, start_neighbor, partition_edge_avoid, old_neighbors)

        if not connected:
            return False

    # All neighbors of all changed nodes are connected, so the new graph is
    # connected.
    return True


def contiguous(partition):
    """Check if the assignment blocks of a partition are connected.

    :parition: :class:`rundmcmc.partition.Partition` instance.
    :flips: Dictionary of proposed flips, with `(nodeid: new_assignment)`
            pairs. If `flips` is `None`, then fallback :func:`.contiguous`.

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
    Checks that a given partition's components are connected using a simple breadth-first search.

    :partition: Instance of Partition; contains connected components.
    :returns: Boolean; Are the components of this partition connected?

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
        if _bfs(adj) is False:
            return False

    return True


def non_bool_fast_connected(partition):
    """
    Return the number of non-connected assignment subgraphs.

    :partition: Instance of Partition; contains connected components.
    :return: int: number of contiguous districts
    """
    assignment = partition.assignment

    # Inverts the assignment dictionary so that lists of VTDs are keyed
    # by their congressional districts.
    districts = collections.defaultdict(set)
    returns = 0

    for vtd in assignment:
        districts[assignment[vtd]].add(vtd)

    # Generates a subgraph for each district and perform a BFS on it
    # to check connectedness.
    for district in districts:
        adj = nx.to_dict_of_lists(partition.graph, districts[district])
        if _bfs(adj):
            returns += 1

    return returns


def non_bool_where(partition):
    """
    Return the number of non-connected assignment subgraphs.

    :partition: Instance of Partition; contains connected components.
    :return: int: number of contiguous districts
    """
    assignment = partition.assignment

    # Inverts the assignment dictionary so that lists of VTDs are keyed
    # by their congressional districts.
    districts = collections.defaultdict(set)
    returns = 0

    for vtd in assignment:
        districts[assignment[vtd]].add(vtd)

    # Generates a subgraph for each district and perform a BFS on it
    # to check connectedness.
    for district in districts:
        adj = nx.to_dict_of_lists(partition.graph, districts[district])
        if _bfs(adj):
            returns += 1
        else:
            print(district)
            nx.draw(partition.graph.subgraph(districts[district]))
            plt.show()
            print(districts[district])
            for subdistrict in nx.connected_components(
                    partition.graph.subgraph(districts[district])):
                nx.draw(partition.graph.subgraph(subdistrict), with_labels=True)
                plt.show()
                print(subdistrict)

    return returns


no_more_disconnected = SelfConfiguringLowerBound(non_bool_fast_connected)


def proposed_changes_still_contiguous(partition):
    """
        Checks whether the districts that are altered by a proposed change
        (stored in partition.flips) remain contiguous under said changes.

        :parition: Current :class:`.Partition` object.

        :returns: True if changed districts are contiguous, False otherwise.
    """

    # Check whether this is the initial partition (parent=None)
    # or one with proposed changes (parent != None).
    districts_of_interest = set(partition.assignment.values())
    if partition.parent:
        if partition.flips.keys is not None:
            districts_of_interest = set(partition.flips.values()).union(
                                        set(map(partition.parent.assignment.get, partition.flips)))
        else:
            districts_of_interest = []

    # Inverts the assignment dictionary so that lists of VTDs are keyed
    # by their congressional districts.
    assignment = partition.assignment
    districts = collections.defaultdict(set)
    for vtd in assignment:
        districts[assignment[vtd]].add(vtd)

    for key in districts_of_interest:
        adj = nx.to_dict_of_lists(partition.graph, districts[key])
        if _bfs(adj) is False:
            return False

    return True


def _bfs(graph):
    """
    Performs a breadth-first search on the provided graph and returns true or
    false depending on whether the graph is connected.

    :graph: Dict-of-lists; an adjacency matrix.
    :returns: Boolean; is this graph connected?

    """
    q = [next(iter(graph))]
    visited = set()
    total_vertices = len(list(graph.keys()))

    # Check if the district has a single vertex. If it does, then simply return
    # `True`, as it's trivially connected.
    if total_vertices <= 1:
        return True

    # bfs!
    while len(q) is not 0:
        current = q.pop(0)
        neighbors = graph[current]

        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                q += [neighbor]

    return total_vertices == len(visited)


def districts_within_tolerance(partition, attribute_name="population", percentage=0.1):
    """
    Check if all districts are within a certain percentage of the "smallest"
    district, as defined by the given attribute.

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


def population_balance(partition, attribute_name="population"):
    """
    Compute the ratio "range / minimum value" of the given attribute on
    assignment blocks.
    """
    values = partition[attribute_name].values()
    max_difference = max(values) - min(values)
    return max_difference / min(values)


def refuse_new_splits(partition_county_field):
    """Refuse all proposals that split a county that was previous unsplit.

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
    """Require that no districts be completely consumed."""
    if not partition.parent:
        return True
    return len(partition) == len(partition.parent)
