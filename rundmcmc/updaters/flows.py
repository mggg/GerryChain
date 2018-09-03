import collections
import functools


def create_flow():
    return {'in': set(), 'out': set()}


def flows_from_changes(old_assignment, flips):
    flows = collections.defaultdict(create_flow)
    for node, target in flips.items():
        source = old_assignment[node]
        if source != target:
            flows[target]['in'].add(node)
            flows[source]['out'].add(node)
    return flows


def on_flow(initializer, alias):
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
                new_values[part] = function(partition, previous[part], flow['in'], flow['out'])

            return new_values
        return wrapped
    return decorator


def compute_edge_flows(partition):
    edge_flows = collections.defaultdict(create_flow)
    assignment = partition.assignment
    old_assignment = partition.parent.assignment
    for node in partition.flips:
        for neighbor in partition.graph.neighbors(node):
            edge = tuple(sorted((node, neighbor)))

            old_source = old_assignment[node]
            old_target = old_assignment[neighbor]

            new_source = assignment[node]
            new_target = assignment[neighbor]

            cut = new_source != new_target
            was_cut = old_source != old_target

            if not cut and was_cut:
                edge_flows[old_target]['out'].add(edge)
                edge_flows[old_source]['out'].add(edge)
            elif cut and not was_cut:
                edge_flows[new_target]['in'].add(edge)
                edge_flows[new_source]['in'].add(edge)
            elif cut and was_cut:
                # If an edge was cut and still is cut, we need to make sure the
                # edge is listed under the correct parts.
                no_longer_incident_parts = {old_target, old_source} - \
                                            {new_target, new_source}
                for part in no_longer_incident_parts:
                    edge_flows[part]['out'].add(edge)

                newly_incident_parts = {new_target, new_source} - {old_target, old_source}
                for part in newly_incident_parts:
                    edge_flows[part]['in'].add(edge)
    return edge_flows


def on_edge_flow(initializer, alias):
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
                new_values[part] = f(partition, previous[part],
                                     new_edges=edge_flows[part]['in'],
                                     old_edges=edge_flows[part]['out'])
            return new_values
        return wrapper
    return decorator
