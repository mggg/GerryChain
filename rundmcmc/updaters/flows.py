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
        def wrapped(partition):
            if not partition.parent:
                return initializer(partition)

            previous = partition.parent[alias]

            new_values = dict()

            for part, flow in partition.flows.items():
                new_values[part] = function(partition, previous[part], flow['in'], flow['out'])

            result = {**previous, **new_values}

            return result
        return wrapped
    return decorator
