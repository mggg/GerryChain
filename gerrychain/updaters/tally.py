import collections
import warnings
import math

from .flows import flows_from_changes, on_flow


class DataTally:
    """
    An updater for tallying numerical data that is not necessarily stored as
    node attributes
    """

    def __init__(self, data, alias):
        """
        :data: a dict or Series indexed by the graph's nodes,
            or the string key for a node attribute containing the Tally's data.
        :alias: the name of the tally in the Partition's `updaters` dictionary
        """
        self.data = data
        self.alias = alias

        def initialize_tally(partition):
            if isinstance(self.data, str):
                nodes = partition.graph.nodes
                attribute = self.data
                self.data = {node: nodes[node][attribute] for node in nodes}

            tally = collections.defaultdict(int)
            for node, part in partition.assignment.items():
                add = self.data[node]

                if math.isnan(add):
                    warnings.warn(
                        "ignoring nan encountered at node '{}' for attribute '{}'".format(
                            node, self.alias))
                else:
                    tally[part] += add
            return tally

        @on_flow(initialize_tally, alias=alias)
        def update_tally(partition, previous, new_nodes, old_nodes):
            inflow = sum(self.data[node] for node in new_nodes)
            outflow = sum(self.data[node] for node in old_nodes)
            return previous + inflow - outflow

        self._call = update_tally

    def __call__(self, partition, previous=None):
        return self._call(partition, previous)


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
            add = self._get_tally_from_node(partition, node)

            if math.isnan(add):
                warnings.warn("ignoring nan encountered at node '{}' for attribute '{}' "
                              "with fields {}".format(node, self.alias, self.fields))
            else:
                tally[part] += add
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
        new_tally = dict(old_tally)

        graph = partition.graph

        for part, flow in flows_from_changes(parent.assignment, flips).items():
            out_flow = compute_out_flow(graph, self.fields, flow)
            in_flow = compute_in_flow(graph, self.fields, flow)
            new_tally[part] = old_tally[part] - out_flow + in_flow

        return new_tally

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
