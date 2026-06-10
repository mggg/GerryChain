import random
from collections import deque
from typing import Any

from ..graph import Graph
from ..partition import Partition
from .bounds import SelfConfiguringLowerBound


def _are_reachable(
    graph: Graph, start_node: Any, mapping: dict[Any, int], part: int, targets: Any
) -> bool:
    """Check if the targets are reachable from the start_node without leaving the given district.

    The search starts inside ``part`` and only ever steps to neighbors that are also in ``part``,
    which is equivalent to (but much cheaper than) calling an avoid-this-edge predicate on every
    edge: one dict lookup per neighbor instead of a Python function call plus two lookups.

    Args:
        graph (Graph): Graph
        start_node (int): The starting node; must be in ``part``
        mapping (dict[Any, int]): The node_id -> part assignment mapping
        part (int): The part (district) the search is confined to
        targets (Any): The target nodes that we would like to reach

    Returns:
        bool: True if all of the targets are reachable from the start_node node
            without leaving ``part``, False otherwise.
    """
    # Track the targets not yet reached in a set so the loop condition is O(1)
    # per iteration; the search stops as soon as the last target is reached.
    unseen_targets = set(targets)
    unseen_targets.discard(start_node)

    seen = {start_node}
    queue = deque((start_node,))
    neighbors = graph.neighbors

    while unseen_targets and queue:
        node_id = queue.popleft()
        for neighbor_node_id in neighbors(node_id):
            if neighbor_node_id not in seen and mapping[neighbor_node_id] == part:
                seen.add(neighbor_node_id)
                unseen_targets.discard(neighbor_node_id)
                queue.append(neighbor_node_id)

    return not unseen_targets


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

    return all(partition.subgraphs[part].is_connected() for part in _affected_parts(partition))


# TODO: Delete this - it is obsolete...
def contiguous_bfs(partition) -> bool:
    raise ("contiguous_bfs() is obsolete")


def number_of_contiguous_parts(partition: Partition) -> int:
    """Computes number of contiguous parts in the partition.

    Args:
        partition (Partition): Instance of Partition; contains connected components.

    Returns:
        int: Number of contiguous parts in the partition.
    """
    parts = partition.assignment.parts
    return sum(1 for part in parts if partition.subgraphs[part].is_connected())


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
