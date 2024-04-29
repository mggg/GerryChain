from heapq import heappop, heappush
from itertools import count

import networkx as nx
from typing import Callable, Any, Dict, Set
from ..partition import Partition
import random
from .bounds import SelfConfiguringLowerBound


def are_reachable(G: nx.Graph, source: Any, avoid: Callable, targets: Any) -> bool:
    """
    A modified version of NetworkX's function
    `networkx.algorithms.shortest_paths.weighted._dijkstra_multisource()`

    This function checks if the targets are reachable from the source node
    while avoiding edges based on the avoid condition function.

    :param G: The networkx graph
    :type G: nx.Graph
    :param source: The starting node
    :type source: int
    :param avoid: The function that determines if an edge should be avoided.
        It should take in three parameters: the start node, the end node, and
        the edges to avoid. It should return True if the edge should be avoided,
        False otherwise.
    :type avoid: Callable
    :param targets: The target nodes that we would like to reach
    :type targets: Any

    :returns: True if all of the targets are reachable from the source node
        under the avoid condition, False otherwise.
    :rtype: bool
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


def single_flip_contiguous(partition: Partition) -> bool:
    """
    Check if swapping the given node from its old assignment disconnects the
    old assignment class.

    :param partition: The proposed next :class:`~gerrychain.partition.Partition`
    :type partition: Partition

    :returns: whether the partition is contiguous
    :rtype: bool

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

    def partition_edge_avoid(start_node: Any, end_node: Any, edge_attrs: Dict):
        """
        Helper function used in the graph traversal to avoid edges that cross between different
        assignments. It's crucial for ensuring that the traversal only considers paths within
        the same assignment class.

        :param start_node: The start node of the edge.
        :type start_node: Any
        :param end_node: The end node of the edge.
        :type end_node: Any
        :param edge_attrs: The attributes of the edge (not used in this function). Needed
            because this function is passed to :func:`are_reachable`, which expects the
            avoid function to have this signature.
        :type edge_attrs: Dict

        :returns: True if the edge should be avoided (i.e., if it crosses assignment classes),
            False otherwise.
        :rtype: bool
        """
        return assignment.mapping[start_node] != assignment.mapping[end_node]

    for changed_node in flips:
        old_assignment = partition.parent.assignment.mapping[changed_node]

        old_neighbors = [
            node
            for node in graph.neighbors(changed_node)
            if assignment.mapping[node] == old_assignment
        ]

        # Under our assumptions, if there are no old neighbors, then the
        # old_assignment district has vanished. It is trivially connected.
        # We consider the empty district to be disconnected.
        if not old_neighbors:
            return False

        start_neighbor = random.choice(old_neighbors)

        # Check if all old neighbors in the same assignment are still reachable.
        connected = are_reachable(
            graph, start_neighbor, partition_edge_avoid, old_neighbors
        )

        if not connected:
            return False

    # All neighbors of all changed nodes are connected, so the new graph is
    # connected.
    return True


def affected_parts(partition: Partition) -> Set[int]:
    """
    Checks which partitions were affected by the change of nodes.

    :param partition: The proposed next :class:`~gerrychain.partition.Partition`
    :type partition: Partition

    :returns: The set of IDs of all parts that gained or lost a node
        when compared to the parent partition.
    :rtype: Set[int]
    """
    flips = partition.flips
    parent = partition.parent

    if flips is None:
        return partition.parts

    if parent is None:
        return set(flips.values())

    affected = set()
    for node, part in flips.items():
        affected.add(part)
        affected.add(parent.assignment.mapping[node])

    return affected


def contiguous(partition: Partition) -> bool:
    """
    Check if the parts of a partition are connected using :func:`networkx.is_connected`.

    :param partition: The proposed next :class:`~gerrychain.partition.Partition`
    :type partition: Partition

    :returns: Whether the partition is contiguous
    :rtype: bool
    """
    return all(
        nx.is_connected(partition.subgraphs[part]) for part in affected_parts(partition)
    )


def contiguous_bfs(partition: Partition) -> bool:
    """
    Checks that a given partition's parts are connected as graphs using a simple
    breadth-first search.

    :param partition: Instance of Partition
    :type partition: Partition

    :returns: Whether the parts of this partition are connected
    :rtype: bool
    """
    parts_to_check = affected_parts(partition)

    # Generates a subgraph for each district and perform a BFS on it
    # to check connectedness.
    for part in parts_to_check:
        adj = nx.to_dict_of_lists(partition.subgraphs[part])
        if _bfs(adj) is False:
            return False

    return True


def number_of_contiguous_parts(partition: Partition) -> int:
    """
    :param partition: Instance of Partition; contains connected components.
    :type partition: Partition

    :returns: Number of contiguous parts in the partition.
    :rtype: int
    """
    parts = partition.assignment.parts
    return sum(1 for part in parts if nx.is_connected(partition.subgraphs[part]))


# Create an instance of SelfConfiguringLowerBound using the number_of_contiguous_parts function.
# This instance, no_more_discontiguous, is configured to maintain a lower bound on the number of
# contiguous parts in a partition. This is still callable since the class
# SelfConfiguringLowerBound implements the __call__ magic method.
no_more_discontiguous = SelfConfiguringLowerBound(number_of_contiguous_parts)


def contiguous_components(partition: Partition) -> Dict[int, list]:
    """
    Return the connected components of each of the subgraphs of the parts
    of the partition.

    :param partition: Instance of Partition; contains connected components.
    :type partition: Partition

    :returns: dictionary mapping each part ID to a list holding the connected
        subgraphs of that part of the partition
    :rtype: dict
    """
    return {
        part: [subgraph.subgraph(nodes) for nodes in nx.connected_components(subgraph)]
        for part, subgraph in partition.subgraphs.items()
    }


def _bfs(graph: Dict[int, list]) -> bool:
    """
    Performs a breadth-first search on the provided graph and returns True or
    False depending on whether the graph is connected.

    :param graph: Dict-of-lists; an adjacency matrix.
    :type graph: Dict[int, list]

    :returns: is this graph connected?
    :rtype: bool
    """
    q = [next(iter(graph))]
    visited = set()
    total_vertices = len(graph)

    # Check if the district has a single vertex. If it does, then simply return
    # `True`, as it's trivially connected.
    if total_vertices <= 1:
        return True

    # bfs!
    while len(q) > 0:
        current = q.pop(0)
        neighbors = graph[current]

        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                q += [neighbor]

    return total_vertices == len(visited)
