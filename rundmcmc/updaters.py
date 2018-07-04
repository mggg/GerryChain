from enum import Enum
import collections
import math


def compute_polsby_popper(area, perimeter):
    return 4 * math.pi * area / perimeter**2


def polsby_popper_updater(partition):
    return {part: compute_polsby_popper(partition['areas'][part], partition['perimeters'][part])
            for part in partition.parts}


def boundary_nodes(partition, alias='boundary_nodes'):
    if partition.parent:
        return partition.parent[alias]
    return {node for node in partition.graph.nodes if partition.graph.nodes[node]['boundary_node']}


def initialize_exterior_boundaries(partition):
    part_boundaries = collections.defaultdict(set)
    for node in partition['boundary_nodes']:
        part_boundaries[partition.assignment[node]].add(node)
    return part_boundaries


def flips(partition):
    return partition.flips


def exterior_boundaries(partition, alias='exterior_boundaries'):
    if not partition.parent:
        return initialize_exterior_boundaries(partition)

    graph_boundary = partition['boundary_nodes']

    parent = partition.parent
    flips = partition.flips

    old_boundaries = parent[alias]
    new_boundaries = collections.defaultdict(set)

    for part, flow in flows_from_changes(parent.assignment, flips).items():
        inflow = {node for node in flow['in'] if node in graph_boundary}
        outflow = {node for node in flow['out']}
        new_boundaries[part] = (old_boundaries[part] | inflow) - outflow

    return new_boundaries


def perimeter_of_part(partition, part):
    """
    Totals up the perimeter of the part in the partition.
    Requires that 'boundary_perim' be a node attribute, 'shared_perim' be an edge
    attribute, 'cut_edges' be an updater, and 'exterior_boundaries' be an updater.
    """
    exterior_perimeter = sum(partition.graph.nodes[node]['boundary_perim']
                             for node in partition['exterior_boundaries'][part])
    inter_part_perimeter = sum(partition.graph.edges[edge]['shared_perim']
                               for edge in partition['cut_edges_by_part'][part])
    return exterior_perimeter + inter_part_perimeter


def perimeters(partition):
    return {part: perimeter_of_part(partition, part) for part in partition.parts}


def put_edges_into_parts(edges, assignment):
    by_part = collections.defaultdict(set)
    for edge in edges:
        # add edge to the sets corresponding to the parts it touches
        by_part[assignment[edge[0]]].add(edge)
        by_part[assignment[edge[1]]].add(edge)
    return by_part


def new_cuts(partition):
    """The edges that were not cut, but now are"""
    return {tuple(sorted((node, neighbor))) for node in partition.flips
            for neighbor in partition.graph[node]
            if partition.crosses_parts((node, neighbor))}


def obsolete_cuts(partition):
    """The edges that were cut, but now are not"""
    return {tuple(sorted((node, neighbor))) for node in partition.flips
            for neighbor in partition.graph.neighbors(node)
            if partition.parent.crosses_parts((node, neighbor)) and
            not partition.crosses_parts((node, neighbor))}


def cut_edges_by_part(partition, alias='cut_edges_by_part'):
    if not partition.parent:
        edges = {tuple(sorted(edge)) for edge in partition.graph.edges
                if partition.crosses_parts(edge)}
        return put_edges_into_parts(edges, partition.assignment)

    new_by_part = put_edges_into_parts(new_cuts(partition), partition.assignment)
    obsolete_by_part = put_edges_into_parts(obsolete_cuts(partition), partition.parent.assignment)

    new_cut_edges = collections.defaultdict(set)
    previous_value = partition.parent[alias]
    for part in partition.parts:
        new_cut_edges[part] = (previous_value[part] | new_by_part[part]) - obsolete_by_part[part]
    return new_cut_edges


def cut_edges(partition):
    parent = partition.parent

    if not parent:
        return {edge for edge in partition.graph.edges
                if partition.crosses_parts(edge)}
    # Edges that weren't cut, but now are cut
    # We sort the tuples to make sure we don't accidentally end
    # up with both (4,5) and (5,4) (for example) in it
    new, obsolete = new_cuts(partition), obsolete_cuts(partition)

    return (parent['cut_edges'] | new) - obsolete


def max_edge_cuts(partition):
    """returns wes computation for max number of edge cuts... not well documented,
    and a vague upper bound (to be made smaller if possible)

    inputs:
    :partition: a partition instance.

    returns: an integer value

    """
    # TODO need number of frozen edges of graph
    numFrozen = 0
    numDists = len(set(partition.assignment.values()))
    return 2 * (2 * len(partition.graph.nodes) + (numDists - numFrozen) - 6)


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
        return f"{party}"

    def name_proportion(party):
        """Returns the Partition attribute name where we'll save the percentage
        of the total vote count for the given party"""
        return f"{party}%"

    tallies = {name_count(column): Tally(column, alias=name_count(column))
               for column in columns}
    total_name = 'total_votes' + election_name
    tallies[total_name] = Tally(columns, alias=total_name)
    proportions = {name_proportion(column): Proportion(
        name_count(column), total_name) for column in columns}
    return {**tallies, **proportions}


class Tally:
    """
    An updater for keeping a tally of one or more node attributes.

    :fields: the list of node attributes that you want to tally. Or a just a
    single attribute name as a string.
    :alias: the aliased name of this Tally (meaning, the key corresponding to
    this Tally in the Partition's updaters dictionary)
    :dtype: the type (int, float, etc.) that you want the tally to have
    """

    def __init__(self, fields, alias=None, dtype=int):
        if not isinstance(fields, list):
            fields = [fields]
        if not alias:
            alias = fields[0]
        self.fields = fields
        self.alias = alias
        self.dtype = dtype

    def __call__(self, partition):
        if not partition.flips or not partition.parent:
            return self._initialize_tally(partition)
        return self._update_tally(partition)

    def _initialize_tally(self, partition):
        """
        Compute the initial district-wide tally of data stored in the "field"
        attribute of nodes.

        :field: Attribute name of data stored in nodes, or a list of attribute
            names that you want to tally together.
        :partition: :class:`Partition` class.

        """
        tally = collections.defaultdict(self.dtype)
        for node, part in partition.assignment.items():
            tally[part] += self._get_tally_from_node(partition, node)
        return tally

    def _update_tally(self, partition):
        """
        Compute the district-wide tally of data stored in the "field" attribute
        of nodes, given proposed changes.

        :fields: Attribute name of data stored in nodes, or a list
            of attribute names that you would like to sum together.
        :partition: :class:`Partition` class.
        :changes: Proposed changes.

        """
        parent = partition.parent
        flips = partition.flips

        old_tally = parent[self.alias]
        new_tally = dict()

        graph = partition.graph

        for part, flow in flows_from_changes(parent.assignment, flips).items():
            out_flow = compute_out_flow(graph, self.fields, flow)
            in_flow = compute_in_flow(graph, self.fields, flow)
            new_tally[part] = old_tally[part] - out_flow + in_flow

        return {**old_tally, **new_tally}

    def _get_tally_from_node(self, partition, node):
        return sum(partition.graph.nodes[node][field] for field in self.fields)


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


def boundary_node_count_of_part(partition, part):
    """
    Counts the nodes on the boundary of a part.
    Requires that 'cut_edges' be an updater, and 'exterior_boundaries' be an updater.
    """

    # Counts the nodes that are on the edge of the (US) state
    state_boundary_count = len(partition['exterior_boundaries'][part])

    # Counts the nodes of the part that share an edge with a different part.
    partition_boundary_count = len(set([x for y in partition['cut_edges_by_part'][part]
                                       for x in y]).intersection(partition.parts[part]))

    return state_boundary_count + partition_boundary_count


def boundary_node_counts(partition):
    return {part: boundary_node_count_of_part(partition, part) for part in partition.parts}


def node_counts(partition):
    return {part: len(partition.parts[part]) for part in partition.parts.keys()}


def compute_discrete_polsby_popper(discrete_area, discrete_perimeter):
    return 4 * math.pi * discrete_area / discrete_perimeter**2


def discrete_polsby_popper_updater(partition):
    return {part: compute_discrete_polsby_popper(partition['node_counts'][part],
                                                 partition['boundary_node_counts'][part])
        for part in partition.parts}
