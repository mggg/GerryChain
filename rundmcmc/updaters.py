import collections


def cut_edges(partition, new_assignment=None, flips=None):
    if not flips:
        return {edge for edge in partition.graph.edges if crosses_parts(partition.assignment, edge)}
    # Edges that weren't cut, but now are cut
    new_cuts = {(node, neighbor) for node in flips.keys()
            for neighbor in partition.graph[node]
            if crosses_parts(new_assignment, (node, neighbor))}
    # Edges that were cut, but now are not
    obsolete_cuts = {(node, neighbor) for node in flips.keys()
            for neighbor in partition.graph[node]
            if not crosses_parts(new_assignment, (node, neighbor))}
    return (partition['cut_edges'] | new_cuts) - obsolete_cuts


def crosses_parts(assignment, edge):
    return assignment[edge[0]] != assignment[edge[1]]


def statistic_factory(field, alias=None):
    """
    Create updater function that updates the district-wide sum of the given
    statistic.

    :field: Attribute key for data stored on nodes.
    :alias: Name to be stored in the chain for the aggregate statistic.
    """
    if not alias:
        alias = field

    def statistic(partition, new_assignment=None, flips=None):
        if not flips:
            return initialize_statistic(field, partition)
        return update_statistic(field, partition[alias], partition, flips)
    return statistic


def initialize_statistic(field, partition):
    """
    Compute the initial district-wide statistic of data stored in the "field"
    attribute of nodes.

    :field: Attribute name of data stored in nodes.
    :partition: :class:`Partition` class.

    """
    statistic = collections.defaultdict(int)
    for node, part in partition.assignment.items():
        statistic[part] += partition.graph.nodes[node][field]
    return statistic


def update_statistic(field, old_statistic, partition, changes):
    """
    Compute the district-wide statistic of data stored in the "field" attribute
    of nodes, given proposed changes.

    :field: Attribute name of data stored in nodes.
    :partition: :class:`Partition` class.
    :changes: Proposed changes.

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
