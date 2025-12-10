from heapq import heappop, heappush
from itertools import count

from typing import Callable, Any, Dict, Set
from ..partition import Partition
import random
from .bounds import SelfConfiguringLowerBound

from ..graph import Graph

# frm: TODO: Performance: Think about the efficiency of the routines in this module.  Almost all
#               of these involve traversing the entire graph, and I fear that callers
#               might make multiple calls.
#
#               Possible solutions are to 1) speed up these routines somehow and 2) cache
#               results so that at least we don't do the traversals over and over.

# frm: TODO: Refactoring: Rethink WTF this module is all about.  
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
    """
    A modified version of NetworkX's function
    `networkx.algorithms.shortest_paths.weighted._dijkstra_multisource()`

    This function checks if the targets are reachable from the start_node node
    while avoiding edges based on the avoid condition function.

    :param graph: Graph
    :type graph: Graph
    :param start_node: The starting node
    :type start_node: int
    :param avoid: The function that determines if an edge should be avoided.
        It should take in three parameters: the start node, the end node, and
        the edges to avoid. It should return True if the edge should be avoided,
        False otherwise.
        # frm: TODO: Documentation:  Fix the comment above about the "avoid" function parameter.
        #               It may have once been accurate, but the original code below
        #               passed parameters to it of (node_id, neighbor_node_id, edge_data_dict)
        #               from NetworkX.Graph._succ  So, "the edges to avoid" above is wrong.
        #               This whole issue is moot, however, since the only routine
        #               that is used as an avoid function ignores the third parameter.
        #               Or rather it used to avoid the third parameter, but it has
        #               been updated to only take two parameters, and the code below
        #               has been modified to use Graph.neighbors() instead of _succ
        #               because 1) we can't use NX and 2) because we don't need the
        #               edge data dictionary anyways...
        #
    :type avoid: Callable
    :param targets: The target nodes that we would like to reach
    :type targets: Any

    :returns: True if all of the targets are reachable from the start_node node
        under the avoid condition, False otherwise.
    :rtype: bool
    """
    push = heappush
    pop = heappop
    node_distances = {}  # dictionary of final distances
    seen = {}
    # fringe is heapq with 3-tuples (distance,c,node)
    # use the count c to avoid comparing nodes (may not be able to)
    c = count()
    fringe = []

    seen[start_node] = 0
    push(fringe, (0, next(c), start_node))

    
    # frm: Original Code:
    #
    # while not all(t in seen for t in targets) and fringe:
    #     (d, _, v) = pop(fringe)
    #     if v in dist:
    #         continue  # already searched this node.
    #     dist[v] = d
    #     for u, e in G_succ[v].items():
    #         if avoid(v, u, e):
    #             continue
    # 
    #         vu_dist = dist[v] + 1
    #         if u not in seen or vu_dist < seen[u]:
    #             seen[u] = vu_dist
    #             push(fringe, (vu_dist, next(c), u))
    # 
    # return all(t in seen for t in targets)
    #



    # While we have not yet seen all of our targets and while there is 
    # still some fringe...
    while not all(tgt in seen for tgt in targets) and fringe:
        (distance, _, node_id) = pop(fringe)
        if node_id in node_distances:
            continue  # already searched this node.
        node_distances[node_id] = distance

        for neighbor in graph.neighbors(node_id):
            if avoid(node_id, neighbor):
                continue

            neighbor_distance = node_distances[node_id] + 1
            if neighbor not in seen or neighbor_distance < seen[neighbor]:
                seen[neighbor] = neighbor_distance
                push(fringe, (neighbor_distance, next(c), neighbor))

    # frm: TODO: Refactoring:  Simplify this code.  It computes distances and counts but
    #               never uses them.  These must be relics of code copied 
    #               from somewhere else where it had more uses...

    return all(tgt in seen for tgt in targets)

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

    def _partition_edge_avoid(start_node: Any, end_node: Any):
        """
        Helper function used in the graph traversal to avoid edges that cross between different
        assignments. It's crucial for ensuring that the traversal only considers paths within
        the same assignment class.

        :param start_node: The start node of the edge.
        :type start_node: Any
        :param end_node: The end node of the edge.
        :type end_node: Any
        :param edge_attrs: The attributes of the edge (not used in this function). Needed
            because this function is passed to :func:`_are_reachable`, which expects the
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
        # The "_partition_edge_avoid" function will prevent searching across 
        # a part (district) boundary
        connected = _are_reachable(
            graph, start_neighbor, _partition_edge_avoid, old_neighbors
        )

        if not connected:
            return False

    # All neighbors of all changed nodes are connected, so the new graph is
    # connected.
    return True


def _affected_parts(partition: Partition) -> Set[int]:
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
    Check if the parts of a partition are connected 

    :param partition: The proposed next :class:`~gerrychain.partition.Partition`
    :type partition: Partition

    :returns: Whether the partition is contiguous
    :rtype: bool
    """

    return all(
        is_connected_bfs(partition.subgraphs[part]) for part in _affected_parts(partition)
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
    """
    :param partition: Instance of Partition; contains connected components.
    :type partition: Partition

    :returns: Number of contiguous parts in the partition.
    :rtype: int
    """
    parts = partition.assignment.parts
    return sum(1 for part in parts if is_connected_bfs(partition.subgraphs[part]))


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
def is_connected_bfs(graph: Graph):
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
