import random
from collections.abc import Callable
from heapq import heappop, heappush
from itertools import count
from typing import Any

from ..graph import Graph
from ..partition import Partition
from .bounds import SelfConfiguringLowerBound


def _are_reachable(graph: Graph, start_node: Any, avoid: Callable, targets: Any) -> bool:
    """A modified version of NetworkX's function
    `networkx.algorithms.shortest_paths.weighted._dijkstra_multisource()`.

    This function checks if the targets are reachable from the start_node node while avoiding
    edges based on the avoid condition function.

    Args:
        graph (Graph): Graph
        start_node (int): The starting node
        avoid (Callable): The function that determines if an edge should be avoided. It should take
            two parameters: the node_ids that define the edge. It should return True if the edge
            should be avoided, False otherwise.
        targets (Any): The target nodes that we would like to reach

    Returns:
        bool: True if all of the targets are reachable from the start_node node under the avoid
            condition, False otherwise.
    """

    # Note: This routine computes some values that it does not return, such as node_distances
    # and a counter, "c".
    #
    # I believe that this is done as an optimization, to keep the algorithm focused on nodes
    # that are "close" to the start_node.  The routine, heappush(), implements a min-heap
    # where the value that has the lowest value is always at the top of the stack.  Given
    # that our stack elements are tuples of the form, (distance to root, count, node_id),
    # the elements at the top of the stack will be those that are closest, and then after
    # that those that we saw first in the algorithm.  This should in most cases keep the
    # algorithm from straying far away from the start_node.
    #
    # This makes sense because we are trying to determine if removing the start_node
    # would cause the district to be discontiguous, which can only happen if the
    # start_node is the only path from two of its neighbors, so we want to keep the
    # search close to the start_node.
    #
    # Also, the loop termination condition:
    #
    #     not all(tgt in seen for tgt in targets)
    #
    # looks expensive, but it is not, because the targets are just the "old"
    # neighbors of the start_node, and hence will be a small number.

    push = heappush
    pop = heappop
    node_distances = {}  # dictionary of final distances
    seen = {}  # dictionary of node_id to node_distance for nodes not yet

    # use the count c to avoid comparing nodes (may not be able to)
    c = count()

    # fringe is heapq with 3-tuples (distance,c,node) where distance is
    # the number of edges from the start_node to the current node.
    fringe = []

    seen[start_node] = 0
    push(fringe, (0, next(c), start_node))

    # While we have not yet seen all of our targets and while there is
    # still some fringe (nodes that we have not yet processed)
    while not all(tgt in seen for tgt in targets) and fringe:
        (distance, _, node_id) = pop(fringe)
        if node_id in node_distances:
            continue  # already searched this node.
        node_distances[node_id] = distance

        # Add all of the neighbors (children) of this node to the stack
        for neighbor_node_id in graph.neighbors(node_id):

            if not avoid(node_id, neighbor_node_id):

                neighbor_distance = node_distances[node_id] + 1
                # if this (neighbor) node has not ever been added to the stack or if
                # we have found a shorter distance to the node, then add it to the stack.
                if neighbor_node_id not in seen or neighbor_distance < seen[neighbor_node_id]:
                    seen[neighbor_node_id] = neighbor_distance
                    push(fringe, (neighbor_distance, next(c), neighbor_node_id))

    return all(tgt in seen for tgt in targets)


def single_flip_contiguous(partition: Partition) -> bool:
    """Check if swapping the given node from its old assignment disconnects the old assignment.


    Args:
        partition (Partition): The proposed next Partition

    Returns:
        bool: whether the partition is contiguous
    """
    parent = partition.parent
    flips = partition.flips
    if not flips or not parent:
        return contiguous(partition)

    graph = partition.graph
    assignment = partition.assignment

    def _partition_edge_avoid(start_node: Any, end_node: Any) -> bool:
        """Helper function used in the graph traversal to avoid edges that cross districts (parts).

        Args:
            start_node (Any): The start node of the edge.
            end_node (Any): The end node of the edge.

        Returns:
            bool: True if the edge should be avoided (i.e., if it crosses from one district to
                another), False otherwise.
        """

        # Return True if both the start_node and end_node are in the same district (part).
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
        # The "_partition_edge_avoid" function will prevent searching across
        # a district (part) boundary
        connected = _are_reachable(graph, start_neighbor, _partition_edge_avoid, old_neighbors)

        if not connected:
            return False

    # All neighbors of all changed nodes are connected, so the new graph is
    # connected.
    return True


def _affected_parts(partition: Partition) -> set[int]:
    """Checks which partitions were affected by the change of nodes.

    Args:
        partition (Partition): The proposed next Partition

    Returns:
        Set[int]: The set of IDs of all parts that gained or lost a node when compared to the
            parent partition.
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
    """Check if the parts of a partition are connected.

    This function checks if the parts of a partition are connected. It returns whether the
    all components of the partition are contiguous.

    Args:
        partition (Partition): The proposed next Partition

    Returns:
        bool: Whether the partition is contiguous
    """

    return all(partition.subgraphs[part].is_connected_bfs() for part in _affected_parts(partition))


def contiguous_bfs(partition: Partition) -> bool:
    """Checks that a given partition's parts are connected as graphs using BFS.

    Args:
        partition (Partition): Instance of Partition

    Returns:
        bool: Whether the parts of this partition are connected
    """

    # frm: TODO: Refactoring:  Figure out why this routine, contiguous_bfs() exists.
    #
    # It is mentioned in __init__.py so maybe it is used externally in legacy code.
    #
    # However, I have changed the code so that it just calls contiguous() and all
    # of the tests pass, so I am going to assume that my comment below is accurate,
    # that is, I am assuming that this function does not need to exist independently
    # except for legacy purposes.  Stated differently, if someone can verify that
    # this routine is NOT needed for legacy purposes, then we can just delete it.
    #
    # It seems to be exactly the same conceptually as contiguous().  It looks
    # at the "affected" parts - those that have changed node
    # assignments from parent, and sees if those parts are
    # contiguous.
    #
    # frm: Original Code:
    #
    #    parts_to_check = _affected_parts(partition)
    #
    #    # Generates a subgraph for each district and perform a BFS on it
    #    # to check connectedness.
    #    for part in parts_to_check:
    #        adj = nx.to_dict_of_lists(partition.subgraphs[part])
    #        if _bfs(adj) is False:
    #            return False
    #
    #    return True

    return contiguous(partition)


def number_of_contiguous_parts(partition: Partition) -> int:
    """Computes number of contiguous parts in the partition.

    Args:
        partition (Partition): Instance of Partition; contains connected components.

    Returns:
        int: Number of contiguous parts in the partition.
    """
    parts = partition.assignment.parts
    return sum(1 for part in parts if partition.subgraphs[part].is_connected_bfs())


# Create an instance of SelfConfiguringLowerBound using the number_of_contiguous_parts function.
# This instance, no_more_discontiguous, is configured to maintain a lower bound on the number of
# contiguous parts in a partition. This is still callable since the class
# SelfConfiguringLowerBound implements the __call__ magic method.
no_more_discontiguous = SelfConfiguringLowerBound(number_of_contiguous_parts)


def contiguous_components(partition: Partition) -> dict[int, list]:
    """Determines the connected components of each of the subgraphs of the parts of the partition.

    Args:
        partition (Partition): Instance of Partition; contains connected components.

    Returns:
        dict: dictionary mapping each part ID to a list holding the connected subgraphs of that
            part of the partition
    """

    # frm: TODO: Documentation: Migration Guide:  NX vs RX Issues here:
    #
    # The call on subgraph() below is perhaps problematic because it will renumber
    # node_ids...
    #
    # The issue is not that the code is incorrect (with RX there is really no other
    # option), but rather that any legacy code will be unprepared to deal with the fact
    # that the subgraphs returned are (I think) three node translations away from the
    # original NX-Graph object's node_ids.
    #
    # Translations:
    #
    #    1) From NX to RX when partition was created
    #    2) From top-level RX graph to the partition's subgraphs for each part (district)
    #    3) From each part's subgraph to the subgraphs of contiguous_components...
    #

    connected_components_in_each_partition = {}
    for part, subgraph in partition.subgraphs.items():
        # create a subgraph for each set of connected nodes in the part's nodes
        list_of_connected_subgraphs = subgraph.subgraphs_for_connected_components()
        connected_components_in_each_partition[part] = list_of_connected_subgraphs

    return connected_components_in_each_partition


def _bfs(graph: dict[int, list]) -> bool:
    """Performs BFS on the provided graph and returns if the graph is connected.

    Args:
        graph (Dict[int, list]): Dict-of-lists; an adjacency matrix.

    Returns:
        bool: is this graph connected?
    """
    q = [next(iter(graph))]
    visited = set()
    num_nodes = len(graph)

    # Check if the district has a single vertex. If it does, then simply return
    # `True`, as it's trivially connected.
    if num_nodes <= 1:
        return True

    # bfs!
    while len(q) > 0:
        current = q.pop(0)
        neighbors = graph[current]

        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                q += [neighbor]

    return num_nodes == len(visited)
