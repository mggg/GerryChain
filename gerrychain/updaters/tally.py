import collections
import math
import warnings
from typing import Dict, List, Optional, Type, Union

import pandas

from .flows import flows_from_changes, on_flow


class DataTally:
    """
    An updater for tallying numerical data that is not necessarily stored as
    node attributes

    Attributes:
        data (Union[Dict, pandas.Series, str]): A Dict or Series indexed by the graph's nodes,
            or the string key for a node attribute containing the Tally's data.
        alias (str): The name of the tally in the Partition's `updaters` dictionary
    """

    # frm: * TODO: Code:  Check to see if DataTally used for data that is NOT attribute of a node
    #
    # The comment above indicates that you can use a DataTally for data that is not stored
    # as an attribute of a node.  Check to see if it is ever actually used that way.  If so,
    # then update the documentation above to state the use cases for adding up data that is
    # NOT stored as a node attribute...
    #
    # It appears that some tests use the ability to specify tallies that do not involve a
    # node attribute, but it is not clear if any "real" code does that...

    __slots__ = ["data", "alias", "_call"]

    def __init__(self, data: Union[Dict, pandas.Series, str], alias: str) -> None:
        """Initialize a DataTally instance.

        Args:
            data (Union[Dict, pandas.Series, str]): A Dict or Series indexed by the graph's nodes,
                or the string key for a node attribute containing the Tally's data.
            alias (str): The name of the tally in the Partition's `updaters` dictionary

        """
        self.data = data
        self.alias = alias

        def initialize_tally(partition):

            # If the "data" passed in was a string, then interpret that string
            # as the name of a node attribute in the graph, and construct
            # a dict of the form: {node_id: node_attribution_value}
            #
            # If not, then assume that the "data" passed in is already of the
            # form: {node_id: data_value}

            if isinstance(self.data, str):
                # if the "data" passed in was a string, then replace its value with
                # a dict of {node_id: attribute_value of the node}
                graph = partition.graph
                node_ids = partition.graph.node_indices
                attribute = self.data
                self.data = {node_id: graph.node_data(node_id)[attribute] for node_id in node_ids}

            tally = collections.defaultdict(int)
            for node_id, part in partition.assignment.items():
                add = self.data[node_id]

                # Note: math.isnan() will raise an exception if the value passed in is not
                # numeric, so there is no need to do another check to ensure that the value
                # is numeric - that test is implicit in math.isnan()
                #
                if math.isnan(add):
                    warnings.warn(
                        "ignoring nan encountered at node_id '{}' for attribute '{}'".format(
                            node_id, self.alias
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

    Attributes:
        fields (Union[str, List[str]]): The list of node attributes that you want to tally. Or just
        a
            single attribute name as a string.
        alias (Optional[str]): The aliased name of this Tally (meaning, the key corresponding to
            this Tally in the Partition's updaters dictionary)
        dtype (Any): The type (int, float, etc.) that you want the tally to have
    """

    __slots__ = ["fields", "alias", "dtype"]

    def __init__(
        self,
        fields: Union[str, List[str]],
        alias: Optional[str] = None,
        dtype: Type = int,
    ) -> None:
        """Initialize a Tally instance.

        Args:
            fields (Union[str, List[str]]): The list of node attributes that you want to tally. Or
                a just a single attribute name as a string.
            alias (Optional[str], optional): The aliased name of this Tally (meaning, the key
                corresponding to this Tally in the Partition's updaters dictionary). Default is
                None.
            dtype (Any, optional): The type (int, float, etc.) that you want the tally to have.
                Default is int.

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
        """Compute initial part-level tallies for the configured field values.

        Args:
            partition (:class:`~gerrychain.partition.Partition`): The partition to compute the
                tally for.

        Returns:
            Dict: A dictionary keyed by the parts of the partition, with values being the sum of
                the "field" attribute of nodes in that part.
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
        """Compute the district-wide tally of data stored in the "field" attribute of nodes.

        Args:
            partition (:class:`~gerrychain.partition.Partition`): The partition to update the tally
                for.

        Returns:
            Dict: A dictionary keyed by the parts of the partition, with the updated tallies of the
                "field" attribute of nodes in each part.
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
        return sum(partition.graph.node_data(node)[field] for field in self.fields)


def compute_out_flow(graph, fields: Union[str, List[str]], flow: Dict) -> int:
    """Return sum of the "field" attribute of nodes in the "out" set of the flow.

    Args:
        graph (:class:`~gerrychain.graph.Graph`): The graph that the partition is defined on.
        fields (Union[str, List[str]]): The list of node attributes that you want to tally. Or just
            a single attribute name as a string.
        flow (Dict): A dictionary containing the flow from the parent of this partition to this
            partition. This dictionary is of the form `{part: {'in': <set of nodes that flowed in>,
            'out': <set of nodes that flowed out>}}`.

    Returns:
        int: The sum of the "field" attribute of nodes in the "out" set of the flow.
    """
    return sum(graph.node_data(node)[field] for node in flow["out"] for field in fields)


def compute_in_flow(graph, fields: Union[str, List[str]], flow: Dict) -> int:
    """Return sum of the "field" attribute of nodes in the "in" set of the flow.

    Args:
        graph (:class:`~gerrychain.graph.Graph`): The graph that the partition is defined on.
        fields (Union[str, List[str]]): The list of node attributes that you want to tally. Or just
            a single attribute name as a string.
        flow (Dict): A dictionary containing the flow from the parent of this partition to this
            partition. This dictionary is of the form `{part: {'in': <set of nodes that flowed in>,
            'out': <set of nodes that flowed out>}}`.

    Returns:
        int: The sum of the "field" attribute of nodes in the "in" set of the flow.
    """
    return sum(graph.node_data(node)[field] for node in flow["in"] for field in fields)
