import collections


def statistic_factory(field, alias=None):
    """statistic_factory returns an updater function that updates the
    district-wide sum of the given statistic.

    :field: the node attribute key
    :alias: the name for the aggregate statistic
    """
    if not alias:
        alias = field

    def statistic(partition, flips=None):
        if not flips:
            return initialize_statistic(field, partition, flips)
        return update_statistic(field, partition[alias], partition, flips)
    return statistic


def initialize_statistic(field, partition, flips=None):
    """initialize_statistic computes the initial sum of the data column
    that we want to sum up for each district at each step.
    """
    statistic = collections.defaultdict(int)
    for node, part in partition.assignment.items():
        statistic[part] += partition.graph.nodes[node][field]
    return statistic


def update_statistic(field, old_statistic, partition, changes):
    """update_statistic returns the updated sum for the specificed statistic
    after changes are incorporated.
    """
    new_statistic = dict()
    for part, flow in flows_from_changes(partition, changes).items():
        out_flow = sum(partition.graph.nodes[node][field] for node in flow['out'])
        in_flow = sum(partition.graph.nodes[node][field] for node in flow['in'])
        new_statistic[part] = old_statistic[part] - out_flow + in_flow
    return {**old_statistic, **new_statistic}


def create_flow():
    return {'in': set(), 'out': set()}


def flows_from_changes(partition, changes):
    flows = collections.defaultdict(create_flow)
    for node, target in changes.items():
        source = partition.assignment[node]
        if source != target:
            flows[target]['in'].add(node)
            flows[source]['out'].add(node)
    return flows
