import random
from collections.abc import Callable
from heapq import heappop, heappush
from itertools import count
from typing import Any

from ..graph import Graph
from ..partition import Partition
from .bounds import SelfConfiguringLowerBound

# frm: TODO: Performance: Think about the efficiency of the routines in this module.
#
# Almost all of these involve traversing the entire graph, and I fear that callers
# might make multiple calls.  Possible solutions are to 1) speed up these routines
# somehow and 2) cache results so that at least we don't do the traversals over and over.

# frm: TODO: Refactoring: Rethink what this module is all about.
#
# It seems like a grab bag for lots of different things - used in different places.
#
# What got me to write this comment was looking at the signature for def contiguous()
# which operates on a partition, but lots of other routines here operate on graphs or
# other things.  So, what is going on?
#
# Peter replied to this comment in a pull request:
#
#     So anything that is prefixed with an underscore in here should be a helper
#     function and not a part of the public API. It looks like, other than
#     is_connected_bfs (which should probably be marked "private" with an
#     underscore) everything here is acting like an updater.
#


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

    # frm: Original Code:
    #
    # Note that the original code used an avoid() function that took three
    # parameters.  That code had been copied from some other codebase and
    # as a result it contained code that was not applicable to GerryChain
    # uses - I forget the specifics, but the GerryChain code did not need
    # to provide three parameters to the avoid function.
    #
    #     while not all(t in seen for t in targets) and fringe:
    #         (d, _, v) = pop(fringe)
    #         if v in dist:
    #             continue  # already searched this node.
    #         dist[v] = d
    #         for u, e in G_succ[v].items():
    #             if avoid(v, u, e):
    #                 continue
    #
    #             vu_dist = dist[v] + 1
    #             if u not in seen or vu_dist < seen[u]:
    #                 seen[u] = vu_dist
    #                 push(fringe, (vu_dist, next(c), u))
    #
    #     return all(t in seen for t in targets)
    #

    # While we have not yet seen all of our targets and while there is
    # still some fringe (nodes that we have not yet processed)
    while not all(tgt in seen for tgt in targets) and fringe:
        (distance, _, node_id) = pop(fringe)
        if node_id in node_distances:
            continue  # already searched this node.
        node_distances[node_id] = distance

        # Add all of the neighbors (children) of this node to the stack
        for neighbor_node_id in graph.neighbors(node_id):
            if avoid(node_id, neighbor_node_id):
                # If the current neighbor is to be avoided, skip it...

                # frm: TODO: Refactoring: Just use if not avoid(node_id,
                # neighbor_node_id) instead of continue.
                #
                # For lots of reasons, it is best to avoid leaving a loop in multiple ways...
                #
                continue

            neighbor_distance = node_distances[node_id] + 1
            # if this (neighbor) node has not ever been added to the stack or if
            # we have found a shorter distance to the node, then add it to the stack.
            if neighbor_node_id not in seen or neighbor_distance < seen[neighbor_node_id]:
                seen[neighbor_node_id] = neighbor_distance
                push(fringe, (neighbor_distance, next(c), neighbor_node_id))

    # frm: TODO: Refactoring:  _are_reachable() computes values it never uses
    #
    # It computes distances and counts but never uses them.  These must be
    # relics of code copied from somewhere else where it had more uses...
    #
    # The variable, "node_distances", stores 1) the fact that a node has been processed
    # and 2) what the distance is for that node from the start_node, but the distance
    # is never used.  In fact, the distance could be anything and the code would work.
    #
    # Similarly, the variable, "seen", stores 1) the fact that a node has been added
    # to the stack at some point in time and 2) the distance to the node from the start_node
    # but the distance is never used.  As with node_distances the value could be anything.
    #
    # The if statement that checks to see if we should add a node to the stack checks
    # to see if the distance for the current path is less than a previously calculated
    # distance, and if so, adds it to the stack - presumably so that at the end we have
    # recorded the shortest distance to each reachable node, but since we never make
    # any use of those distances, this test is not useful.
    #
    # *sigh*
    #
    # Peter said (January 2026): Yeah, it looks like this is a modified version of
    # multisource Dijkstra. All that really needs to be done here is make sure that
    # there is some path between all the nodes that doesn't cross partition
    # boundaries. It doesn't need to be the shortest path (which is what
    # Dijkstra computes).

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

    return all(is_connected_bfs(partition.subgraphs[part]) for part in _affected_parts(partition))


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
    return sum(1 for part in parts if is_connected_bfs(partition.subgraphs[part]))


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


# frm: TODO: Testing:  Verify that is_connected_bfs() works - add a test or two...

# frm: TODO: Refactoring:  Move this code into graph.py.  It is all about the Graph...


# frm: TODO: Documentation: This code was obtained from the web - probably could be optimized...
#       This code replaced calls on nx.is_connected()
def is_connected_bfs(graph: Graph) -> bool:
    if not graph:
        return True

    nodes = list(graph.node_indices)

    start_node = random.choice(nodes)
    visited = {start_node}
    queue = [start_node]

    while queue:
        current_node = queue.pop(0)
        for neighbor in graph.neighbors(current_node):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return len(visited) == len(nodes)
