import collections
import math


def touches_part(edge, part, partition):
    return partition.assignment[edge[0]] == part or partition.assignment[edge[1]] == part


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


def cut_edges_by_part(partition, alias='cut_edges'):
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
