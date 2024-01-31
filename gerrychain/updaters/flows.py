import collections
import functools
from typing import Dict, Set, Tuple, Callable


@functools.lru_cache(maxsize=2)
def neighbor_flips(partition) -> Set[Tuple]:
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: The set of edges that were flipped in the given partition.
    :rtype: Set[Tuple]
    """
    return {
        tuple(sorted((node, neighbor)))
        for node in partition.flips
        for neighbor in partition.graph.neighbors(node)
    }


def create_flow():
    return {"in": set(), "out": set()}


@functools.lru_cache(maxsize=2)
def flows_from_changes(old_partition, new_partition) -> Dict:
    """
    :param old_partition: A partition of a Graph representing the previous step.
    :type old_partition: :class:`~gerrychain.partition.Partition`
    :param new_partition: A partition of a Graph representing the current step.
    :type new_partition: :class:`~gerrychain.partition.Partition`

    :returns: A dictionary mapping each node that changed assignment between
        the previous and current partitions to a dictionary of the form
        `{'in': <set of nodes that flowed in>, 'out': <set of nodes that flowed out>}`.
    :rtype: Dict
    """
    flows = collections.defaultdict(create_flow)
    for node, target in new_partition.flips.items():
        source = old_partition.assignment.mapping[node]
        if source != target:
            flows[target]["in"].add(node)
            flows[source]["out"].add(node)
    return flows


def on_flow(initializer: Callable, alias: str) -> Callable:
    """
    Use this decorator to create an updater that responds to flows of nodes
    between parts of the partition.

    Decorate a function that takes:
    - The partition
    - The previous value of the updater on a fixed part P_i
    - The new nodes that are just joining P_i at this step
    - The old nodes that are just leaving P_i at this step
    and returns:
    - The new value of the updater for the fixed part P_i.

    This will create an updater whose values are dictionaries of the
    form `{part: <value of the given function on the part>}`.

    The initializer, by contrast, should take the entire partition and
    return the entire `{part: <value>}` dictionary.

    Example:

    .. code-block:: python

        @on_flow(initializer, alias='my_updater')
        def my_updater(partition, previous, new_nodes, old_nodes):
            # return new value for the part

    :param initializer: A function that takes the partition and returns a
        dictionary of the form `{part: <value>}`.
    :type initializer: Callable
    :param alias: The name of the updater to be created.
    :type alias: str

    :returns: A decorator that takes a function as input and returns a
        wrapped function.
    :rtype: Callable
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapped(partition, previous=None):
            if partition.parent is None:
                return initializer(partition)

            if previous is None:
                previous = partition.parent[alias]

            new_values = previous.copy()

            for part, flow in partition.flows.items():
                new_values[part] = function(
                    partition, previous[part], flow["in"], flow["out"]
                )

            return new_values

        return wrapped

    return decorator


def compute_edge_flows(partition) -> Dict:
    """
    :param partition: A partition of a Graph
    :type partition: :class:`~gerrychain.partition.Partition`

    :returns: A flow dictionary containing the flow from the parent of this partition
        to this partition. This dictionary is of the form
        `{part: {'in': <set of edges that flowed in>, 'out': <set of edges that flowed out>}}`.
    :rtype: Dict
    """
    edge_flows = collections.defaultdict(create_flow)
    assignment = partition.assignment
    old_assignment = partition.parent.assignment

    for node, neighbor in neighbor_flips(partition):
        edge = (node, neighbor)

        old_source = old_assignment.mapping[node]
        old_target = old_assignment.mapping[neighbor]

        new_source = assignment.mapping[node]
        new_target = assignment.mapping[neighbor]

        cut = new_source != new_target
        was_cut = old_source != old_target

        if not cut and was_cut:
            edge_flows[old_target]["out"].add(edge)
            edge_flows[old_source]["out"].add(edge)
        elif cut and not was_cut:
            edge_flows[new_target]["in"].add(edge)
            edge_flows[new_source]["in"].add(edge)
        elif cut and was_cut:
            # If an edge was cut and still is cut, we need to make sure the
            # edge is listed under the correct parts.
            no_longer_incident_parts = {old_target, old_source} - {
                new_target,
                new_source,
            }
            for part in no_longer_incident_parts:
                edge_flows[part]["out"].add(edge)

            newly_incident_parts = {new_target, new_source} - {old_target, old_source}
            for part in newly_incident_parts:
                edge_flows[part]["in"].add(edge)
    return edge_flows


def on_edge_flow(initializer: Callable, alias: str) -> Callable:
    """
    Use this decorator to create an updater that responds to flows of cut
    edges between parts of the partition.

    Decorate a function that takes:
    - The partition
    - The previous value of the updater for a fixed part P_i
    - The new cut edges that are just joining P_i at this step
    - The old cut edges that are just leaving P_i at this step
    and returns:
    - The new value of the updater for the fixed part P_i.

    This will create an updater whose values are dictionaries of the
    form `{part: <value of the given function on the part>}`.

    The initializer, by contrast, should take the entire partition and
    return the entire `{part: <value>}` dictionary.

    Example:

    .. code-block:: python

        @on_edge_flow(initializer, alias='my_updater')
        def my_updater(partition, previous, new_edges, old_edges):
            # return new value of the part

    :param initializer: A function that takes the partition and returns a
        dictionary of the form `{part: <value>}`.
    :type initializer: Callable
    :param alias: The name of the updater to be created.
    :type alias: str

    :returns: A decorator that takes a function as input and returns a
        wrapped function.
    :rtype: Callable
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapper(partition):
            if not partition.parent:
                return initializer(partition)
            edge_flows = partition.edge_flows
            previous = partition.parent[alias]

            new_values = previous.copy()
            for part in partition.edge_flows:
                new_values[part] = f(
                    partition,
                    previous[part],
                    new_edges=edge_flows[part]["in"],
                    old_edges=edge_flows[part]["out"],
                )
            return new_values

        return wrapper

    return decorator
