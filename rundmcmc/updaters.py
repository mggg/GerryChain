import collections


def cut_edges(partition):
    parent = partition.parent
    flips = partition.flips
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


def tally_factory(field, alias=None, dtype=int):
    """
    Create updater function that updates the district-wide sum of the given
    tally.

    :field: Attribute key for data stored on nodes.
    :alias: Name to be stored in the chain for the aggregate tally.
    """
    if not alias:
        alias = field

    def tally(partition):
        parent = partition.parent
        flips = partition.flips
        if not flips or not parent:
            return initialize_tally(field, partition)
        return update_tally(field, alias, parent, partition, flips)
    return tally


def initialize_tally(field, partition, dtype=int):
    """
    Compute the initial district-wide tally of data stored in the "field"
    attribute of nodes.

    :field: Attribute name of data stored in nodes.
    :partition: :class:`Partition` class.

    """
    tally = collections.defaultdict(dtype)
    for node, part in partition.assignment.items():
        tally[part] += partition.graph.nodes[node][field]
    return tally


def update_tally(field, alias, parent, partition, flips):
    """
    Compute the district-wide tally of data stored in the "field" attribute
    of nodes, given proposed changes.

    :field: Attribute name of data stored in nodes.
    :partition: :class:`Partition` class.
    :changes: Proposed changes.

    """
    old_tally = parent[alias]
    new_tally = dict()
    graph = partition.graph
    for part, flow in flows_from_changes(parent.assignment, flips).items():
        out_flow = sum(graph.nodes[node][field] for node in flow['out'])
        in_flow = sum(graph.nodes[node][field] for node in flow['in'])
        new_tally[part] = old_tally[part] - out_flow + in_flow

    return {**old_tally, **new_tally}


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
