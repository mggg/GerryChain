import collections
import math
import warnings

from .flows import flows_from_changes, on_flow
from typing import Dict, Union, List, Optional, Type
import pandas


class DataTally:
    """
    An updater for tallying numerical data that is not necessarily stored as
    node attributes

    :ivar data: A Dict or Series indexed by the graph's nodes,
        or the string key for a node attribute containing the Tally's data.
    :type data: Union[Dict, pandas.Series, str]
    :ivar alias: The name of the tally in the Partition's `updaters` dictionary
    :type alias: str
    """

    __slots__ = ["data", "alias", "_call"]

    def __init__(self, data: Union[Dict, pandas.Series, str], alias: str) -> None:
        """
        :param data: A Dict or Series indexed by the graph's nodes,
            or the string key for a node attribute containing the Tally's data.
        :type data: Union[Dict, pandas.Series, str]
        :param alias: The name of the tally in the Partition's `updaters` dictionary
        :type alias: str

        :returns: None
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
                            node, self.alias
                        )
                    )
                else:
                    tally[part] += add
            return dict(tally)

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

    :ivar fields: The list of node attributes that you want to tally. Or just a
        single attribute name as a string.
    :type fields: Union[str, List[str]]
    :ivar alias: The aliased name of this Tally (meaning, the key corresponding to
        this Tally in the Partition's updaters dictionary)
    :type alias: Optional[str]
    :ivar dtype: The type (int, float, etc.) that you want the tally to have
    :type dtype: Any
    """

    __slots__ = ["fields", "alias", "dtype"]

    def __init__(
        self,
        fields: Union[str, List[str]],
        alias: Optional[str] = None,
        dtype: Type = int,
    ) -> None:
        """
        :param fields: The list of node attributes that you want to tally. Or a just a
            single attribute name as a string.
        :type fields: Union[str, List[str]]
        :param alias: The aliased name of this Tally (meaning, the key corresponding to
            this Tally in the Partition's updaters dictionary).
            Default is None.
        :type alias: Optional[str], optional
        :param dtype: The type (int, float, etc.) that you want the tally to have.
            Default is int.
        :type dtype: Any, optional

        :returns: None
        """
        if not isinstance(fields, list):
            fields = [fields]
        if not alias:
            alias = fields[0]
        self.fields = fields
        self.alias = alias
        self.dtype = dtype

    def __call__(self, partition):
        if partition.parent is None:
            return self._initialize_tally(partition)
        return self._update_tally(partition)

    def _initialize_tally(self, partition) -> Dict:
        """
        Compute the initial district-wide tally of data stored in the "field"
        attribute of nodes.

        :param partition: The partition to compute the tally for.
        :type partition: :class:`~gerrychain.partition.Partition`

        :returns: A dictionary keyed by the parts of the partition, with values
            being the sum of the "field" attribute of nodes in that part.
        :rtype: Dict
        """
        tally = collections.defaultdict(self.dtype)
        for node, part in partition.assignment.items():
            add = self._get_tally_from_node(partition, node)

            if math.isnan(add):
                warnings.warn(
                    "ignoring nan encountered at node '{}' for attribute '{}' "
                    "with fields {}".format(node, self.alias, self.fields)
                )
            else:
                tally[part] += add
        return dict(tally)

    def _update_tally(self, partition):
        """
        Compute the district-wide tally of data stored in the "field" attribute
        of nodes, given proposed changes.

        :param partition: The partition to update the tally for.
        :type partition: :class:`~gerrychain.partition.Partition`

        :returns: A dictionary keyed by the parts of the partition, with
            the updated tallies of the "field" attribute of nodes in each part.
        :rtype: Dict
        """
        parent = partition.parent

        old_tally = parent[self.alias]
        new_tally = dict(old_tally)

        graph = partition.graph

        for part, flow in flows_from_changes(parent, partition).items():
            out_flow = compute_out_flow(graph, self.fields, flow)
            in_flow = compute_in_flow(graph, self.fields, flow)
            new_tally[part] = old_tally[part] - out_flow + in_flow

        return new_tally

    def _get_tally_from_node(self, partition, node):
        return sum(partition.graph.lookup(node, field) for field in self.fields)


def compute_out_flow(graph, fields: Union[str, List[str]], flow: Dict) -> int:
    """
    :param graph: The graph that the partition is defined on.
    :type graph: :class:`~gerrychain.graph.Graph`
    :param fields: The list of node attributes that you want to tally. Or just a
        single attribute name as a string.
    :type fields: Union[str, List[str]]
    :param flow: A dictionary containing the flow from the parent of this partition
        to this partition. This dictionary is of the form
        `{part: {'in': <set of nodes that flowed in>, 'out': <set of nodes that flowed out>}}`.
    :type flow: Dict

    :returns: The sum of the "field" attribute of nodes in the "out" set of the flow.
    :rtype: int
    """
    return sum(graph.lookup(node, field) for node in flow["out"] for field in fields)


def compute_in_flow(graph, fields: Union[str, List[str]], flow: Dict) -> int:
    """
    :param graph: The graph that the partition is defined on.
    :type graph: :class:`~gerrychain.graph.Graph`
    :param fields: The list of node attributes that you want to tally. Or just a
        single attribute name as a string.
    :type fields: Union[str, List[str]]
    :param flow: A dictionary containing the flow from the parent of this partition
        to this partition. This dictionary is of the form
        `{part: {'in': <set of nodes that flowed in>, 'out': <set of nodes that flowed out>}}`.
    :type flow: Dict

    :returns: The sum of the "field" attribute of nodes in the "in" set of the flow.
    :rtype: int
    """
    return sum(graph.lookup(node, field) for node in flow["in"] for field in fields)
