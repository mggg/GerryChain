from heapq import heappop, heappush
from itertools import count

import networkx as nx

from ..random import random
from .bounds import SelfConfiguringLowerBound


def are_reachable(G, source, avoid, targets):
    """Check that source can reach targets while avoiding given edges.
    This function is a modified form of NetworkX's ``_dijkstra_multisource()``.

    :param G: NetworkX graph.
    :param source: Starting node.
    :param weight: Function with (u, v, data) input that returns that edges weight.
    :param targets: Nodes required to find.
    :return:
        A mapping from node to shortest distance to that node from one
        of the source nodes.
    :rtype: dict
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
    """Check if swapping the given node from its old assignment disconnects the
    old assignment class.

    :param partition: The proposed next :class:`~gerrychain.partition.Partition`

    :return: whether the partition is contiguous
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

    def partition_edge_avoid(start_node, end_node, edge_attrs):
        """Compute the district edge weight, which is 1 if the nodes have the same
        assignment, and infinity otherwise.
        """
        if assignment[start_node] != assignment[end_node]:
            # Fun fact: networkx actually refuses to take edges with None
            # weight.
            return True

        return False

    for changed_node in flips:
        old_assignment = partition.parent.assignment[changed_node]

        old_neighbors = [
            node
            for node in graph.neighbors(changed_node)
            if assignment[node] == old_assignment
        ]

        if not old_neighbors:
            # Under our assumptions, if there are no old neighbors, then the
            # old_assignment district has vanished. It is trivially connected.

            # However, we actually don't want any districts to disappear because
            # it ends up breaking a lot of our other updaters. So we consider
            # the empty district to be disconnected.
            return False

        start_neighbor = random.choice(old_neighbors)

        connected = are_reachable(
            graph, start_neighbor, partition_edge_avoid, old_neighbors
        )

        if not connected:
            return False

    # All neighbors of all changed nodes are connected, so the new graph is
    # connected.
    return True


def affected_parts(partition):
    """Returns the set of IDs of all parts that gained or lost a node during the last
    flip.
    """
    flips = partition.flips
    parent = partition.parent

    if flips is None:
        return partition.parts

    affected = set()
    for node, part in flips.items():
        affected.add(part)
        affected.add(parent.assignment[node])

    return affected


def contiguous(partition):
    """Check if the parts of a partition are connected using :func:`networkx.is_connected`.

    :param partition: The proposed next :class:`~gerrychain.partition.Partition`

    :return: whether the partition is contiguous
    :rtype: bool
    """
    return all(
        nx.is_connected(partition.subgraphs[part]) for part in affected_parts(partition)
    )


def contiguous_bfs(partition):
    """Checks that a given partition's parts are connected as graphs using a simple
    breadth-first search.

    :param partition: Instance of Partition
    :return: Whether the parts of this partition are connected
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


def number_of_contiguous_parts(partition):
    """Return the number of non-connected assignment subgraphs.

    :param partition: Instance of Partition; contains connected components.
    :return: number of contiguous districts
    :rtype: int
    """
    parts = partition.assignment.parts
    return sum(1 for part in parts if nx.is_connected(partition.subgraphs[part]))


def contiguous_components(partition):
    """Return then connected components of each of the subgraphs of the parts
    of the partition.

    :param partition: Instance of Partition; contains connected components.
    :return: dictionary mapping each part ID to a list holding the connected
        subgraphs of that part of the partition
    :rtype: dict
    """
    return {
        part: [subgraph.subgraph(nodes) for nodes in nx.connected_components(subgraph)]
        for part, subgraph in partition.subgraphs.items()
    }


no_more_discontiguous = SelfConfiguringLowerBound(number_of_contiguous_parts)


def _bfs(graph):
    """Performs a breadth-first search on the provided graph and returns true or
    false depending on whether the graph is connected.

    :param graph: Dict-of-lists; an adjacency matrix.
    :return: is this graph connected?
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
