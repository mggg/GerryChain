import collections


def cut_edges(partition, parent=None, flips=None):
    if not parent:
        return {edge for edge in partition.graph.edges
                if partition.crosses_parts(edge)}
    # Edges that weren't cut, but now are cut
    new_cuts = {(node, neighbor) for node in flips.keys()
            for neighbor in partition.graph[node]
            if partition.crosses_parts((node, neighbor))}
    # Edges that were cut, but now are not
    obsolete_cuts = {(node, neighbor) for node in flips.keys()
            for neighbor in partition.graph[node]
            if not partition.crosses_parts((node, neighbor))}
    return (parent['cut_edges'] | new_cuts) - obsolete_cuts


def statistic_factory(field, alias=None, dtype=int):
    """
    Create updater function that updates the district-wide sum of the given
    statistic.

    :field: Attribute key for data stored on nodes.
    :alias: Name to be stored in the chain for the aggregate statistic.
    """
    if not alias:
        alias = field

    def statistic(partition, parent=None, flips=None):
        if not flips or not parent:
            return initialize_statistic(field, partition)
        return update_statistic(field, alias, parent, partition, flips)
    return statistic


def initialize_statistic(field, partition, dtype=int):
    """
    Compute the initial district-wide statistic of data stored in the "field"
    attribute of nodes.

    :field: Attribute name of data stored in nodes.
    :partition: :class:`Partition` class.

    """
    statistic = collections.defaultdict(dtype)
    for node, part in partition.assignment.items():
        statistic[part] += partition.graph.nodes[node][field]
    return statistic


def update_statistic(field, alias, parent, partition, flips):
    """
    Compute the district-wide statistic of data stored in the "field" attribute
    of nodes, given proposed changes.

    :field: Attribute name of data stored in nodes.
    :partition: :class:`Partition` class.
    :changes: Proposed changes.

    """
    old_statistic = parent[alias]
    new_statistic = dict()
    graph = partition.graph
    for part, flow in flows_from_changes(parent.assignment, flips).items():
        out_flow = sum(graph.nodes[node][field] for node in flow['out'])
        in_flow = sum(graph.nodes[node][field] for node in flow['in'])
        new_statistic[part] = old_statistic[part] - out_flow + in_flow

    return {**old_statistic, **new_statistic}


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
