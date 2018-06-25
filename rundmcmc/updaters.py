from enum import Enum
import collections
import math


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


class Proportion:
    def __init__(self, tally_name, total_name):
        self.tally_name = tally_name
        self.total_name = total_name

    def __call__(self, partition):
        return {part: partition[self.tally_name][part] / partition[self.total_name][part]
                if partition[self.total_name][part] > 0
                else math.nan
                for part in partition.parts}


def votes_updaters(columns, election_name=''):
    """
    Returns a dictionary of updaters that tally total votes and compute
    vote share. Example: `votes_updaters(['D','R'], election_name='08')` would
    have entries `'R'`, `'D'`, `'total_votes'` (the tallies) as well as
    `'R%'`, `'D%'` (the percentages of the total vote).

    :columns: the names of the node attributes storing vote counts for each
        party that you are interested in
    :election_name: an optional identifier that will be appended to the names of the
        returned updaters. This is in order to support computing scores
        for multiple elections at the same time, so that the names of the
        updaters don't collide.
    """

    def name_count(party):
        """Return the Partition attribute name where we'll save the total
        vote count for a party"""
        return f"{party}_count"

    def name_proportion(party):
        """Returns the Partition attribute name where we'll save the percentage
        of the total vote count for the given party"""
        return f"{party}%"

    tallies = {name_count(column): tally_factory(column, alias=name_count(column))
               for column in columns}
    total_name = 'total_votes' + election_name
    tallies[total_name] = tally_factory(columns, alias=total_name)
    proportions = {name_proportion(column): Proportion(
        name_count(column), total_name) for column in columns}
    return {**tallies, **proportions}


def tally_factory(fields, alias=None, dtype=int):
    """
    Create updater function that updates the district-wide sum of the given
    tally.

    :field: Attribute key for data stored on nodes, or a list of attribute
        keys that you would like to tally together.
    :alias: Name to be stored in the chain for the aggregate tally.
        Defaults to the given field, or the first in the list of fields if
        a list of fields is given.
    """
    if not isinstance(fields, list):
        fields = [fields]
    if not alias:
        alias = fields[0]

    def tally(partition):
        parent = partition.parent
        flips = partition.flips
        if not flips or not parent:
            return initialize_tally(fields, partition)
        return update_tally(fields, alias, parent, partition, flips)
    return tally


def initialize_tally(fields, partition, dtype=int):
    """
    Compute the initial district-wide tally of data stored in the "field"
    attribute of nodes.

    :field: Attribute name of data stored in nodes, or a list of attribute
        names that you want to tally together.
    :partition: :class:`Partition` class.

    """
    tally = collections.defaultdict(dtype)
    for node, part in partition.assignment.items():
        tally[part] += sum_up_node_attributes(partition.graph, node, fields)
    return tally


def sum_up_node_attributes(graph, node, attributes):
    return sum(graph.nodes[node][field] for field in attributes)


def update_tally(fields, alias, parent, partition, flips):
    """
    Compute the district-wide tally of data stored in the "field" attribute
    of nodes, given proposed changes.

    :fields: Attribute name of data stored in nodes, or a list
        of attribute names that you would like to sum together.
    :partition: :class:`Partition` class.
    :changes: Proposed changes.

    """
    old_tally = parent[alias]
    new_tally = dict()
    graph = partition.graph
    for part, flow in flows_from_changes(parent.assignment, flips).items():
        out_flow = compute_out_flow(graph, fields, flow)
        in_flow = compute_in_flow(graph, fields, flow)
        new_tally[part] = old_tally[part] - out_flow + in_flow

    return {**old_tally, **new_tally}


def compute_out_flow(graph, fields, flow):
    return sum(graph.nodes[node][field]
               for node in flow['out']
               for field in fields)


def compute_in_flow(graph, fields, flow):
    return sum(graph.nodes[node][field]
               for node in flow['in']
               for field in fields)


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


CountyInfo = collections.namedtuple("CountyInfo", "split nodes contains")


class CountySplit(Enum):
    NOT_SPLIT = 0
    NEW_SPLIT = 1
    OLD_SPLIT = 2


def county_splits(partition_name, county_field_name):
    """Track county splits.

    :partition_name: Name that the :class:`.Partition` instance will store.
    :county_field_name: Name of county ID field on the graph.

    :returns: The tracked data is a dictionary keyed on the county ID. The
              stored values are tuples of the form `(split, nodes, seen)`.
              `split` is a :class:`.CountySplit` enum, `nodes` is a list of
              node IDs, and `seen` is a list of assignment IDs that are
              contained in the county.

    """
    def _get_county_splits(partition):
        return compute_county_splits(partition, county_field_name,
                                     partition_name)

    return _get_county_splits


def compute_county_splits(partition, county_field, partition_field):
    """Track nodes in counties and information about their splitting."""

    # Create the initial county data containers.
    if not partition.parent:
        county_dict = dict()

        for node in partition.graph:
            county = partition.graph.nodes[node][county_field]
            if county in county_dict:
                split, nodes, seen = county_dict[county]
            else:
                split, nodes, seen = CountySplit.NOT_SPLIT, [], set()

            nodes.append(node)
            seen.update(set([partition.assignment[node]]))

            if len(seen) > 1:
                split = CountySplit.OLD_SPLIT

            county_dict[county] = CountyInfo(split, nodes, seen)

        return county_dict

    new_county_dict = dict()

    parent = partition.parent
    for county, county_info in parent[partition_field].items():
        seen = set(partition.assignment[node] for node in county_info.nodes)

        split = CountySplit.NOT_SPLIT

        if len(seen) > 1:
            if county_info.split != CountySplit.OLD_SPLIT:
                split = CountySplit.NEW_SPLIT
            else:
                split = CountySplit.OLD_SPLIT

        new_county_dict[county] = CountyInfo(split, county_info.nodes, seen)

    return new_county_dict
