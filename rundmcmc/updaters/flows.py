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
    def decorator(function):
        @functools.wraps(function)
        def wrapped(partition):
            if not partition.parent:
                return initializer(partition)

            previous = partition.parent[alias]

            result = collections.defaultdict(previous.default_factory)

            for part, flow in partition.flows.items():
                result[part] = function(partition, previous[part], flow['in'], flow['out'])

            return result
        return wrapped
    return decorator
