from __future__ import annotations

import collections
import math
import warnings
from collections.abc import Callable, Hashable, Mapping
from typing import TYPE_CHECKING, cast

import pandas

from .flows import flows_from_changes, on_flow

if TYPE_CHECKING:
    from ..graph.graph import FrozenGraph, Graph
    from ..partition.partition import Partition


class DataTally:
    """
    An updater for tallying numerical data that is not necessarily stored as
    node attributes

    Attributes:
        data (dict | pandas.Series | str): A Dict or Series indexed by the graph's nodes,
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

    def __init__(
        self,
        data: Mapping[Hashable, float] | pandas.Series | str,
        alias: str,
    ) -> None:
        """Initialize a DataTally instance.

        Args:
            data (dict | pandas.Series | str): A Dict or Series indexed by the graph's nodes,
                or the string key for a node attribute containing the Tally's data.
            alias (str): The name of the tally in the Partition's `updaters` dictionary

        """
        self.data = data
        self.alias = alias

        def initialize_tally(partition: Partition) -> dict[Hashable, float]:
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

            tally: dict[Hashable, float] = collections.defaultdict(int)
            for node_id, part in partition.assignment.items():
                add = self._value(node_id)

                # Note: math.isnan() will raise an exception if the value passed in is not
                # numeric, so there is no need to do another check to ensure that the value
                # is numeric - that test is implicit in math.isnan()
                #
                if math.isnan(add):
                    warnings.warn(
                        f"ignoring nan encountered at node_id '{node_id}' "
                        f"for attribute '{self.alias}'"
                    )
                else:
                    tally[part] += add

            return dict(tally)

        @on_flow(initialize_tally, alias=alias)
        def update_tally(
            partition: Partition,
            previous: float,
            new_nodes: set[Hashable],
            old_nodes: set[Hashable],
        ) -> float:
            inflow = sum(self._value(node) for node in new_nodes)
            outflow = sum(self._value(node) for node in old_nodes)
            return previous + inflow - outflow

        self._call = update_tally

    def _value(self, node: Hashable) -> float:
        if isinstance(self.data, str):
            raise RuntimeError("Tally data has not been initialized")
        return cast(float, self.data[node])

    def __call__(
        self, partition: Partition, previous: dict[Hashable, float] | None = None
    ) -> dict[Hashable, float]:
        return self._call(partition, previous)


class Tally:
    """
    An updater for keeping a tally of one or more node attributes.

    Attributes:
        fields (str | list[str]): The list of node attributes that you want to tally. Or just
        a
            single attribute name as a string.
        alias (str | None): The aliased name of this Tally (meaning, the key corresponding to
            this Tally in the Partition's updaters dictionary)
        dtype (Callable[[], float]): A zero-argument callable that creates the tally's initial
            value.
    """

    __slots__ = ["fields", "alias", "dtype"]

    def __init__(
        self,
        fields: str | list[str],
        alias: str | None = None,
        dtype: Callable[[], float] = int,
    ) -> None:
        """Initialize a Tally instance.

        Args:
            fields (str | list[str]): The list of node attributes that you want to tally. Or
                a just a single attribute name as a string.
            alias (str | None, optional): The aliased name of this Tally (meaning, the key
                corresponding to this Tally in the Partition's updaters dictionary). Default is
                None.
            dtype (Callable[[], float], optional): A zero-argument callable that creates the
                tally's initial value. Defaults to ``int``.

        """
        if not isinstance(fields, list):
            fields = [fields]
        if not alias:
            alias = fields[0]
        self.fields = fields
        self.alias = alias
        self.dtype = dtype

    def __call__(self, partition: Partition) -> dict[Hashable, float]:
        if partition.parent is None:
            return self._initialize_tally(partition)
        return self._update_tally(partition)

    def _initialize_tally(self, partition: Partition) -> dict[Hashable, float]:
        """Compute initial part-level tallies for the configured field values.

        Args:
            partition (Partition): The partition to compute the
                tally for.

        Returns:
            dict: A dictionary keyed by the parts of the partition, with values being the sum of
                the "field" attribute of nodes in that part.
        """
        tally = collections.defaultdict(self.dtype)
        for node, part in partition.assignment.items():
            add = self._get_tally_from_node(partition, node)

            if math.isnan(add):
                warnings.warn(
                    f"ignoring nan encountered at node '{node}' for attribute '{self.alias}' "
                    f"with fields {self.fields}"
                )
            else:
                tally[part] += add
        return dict(tally)

    def _update_tally(self, partition: Partition) -> dict[Hashable, float]:
        """Compute the district-wide tally of data stored in the "field" attribute of nodes.

        Args:
            partition (Partition): The partition to update the tally
                for.

        Returns:
            dict: A dictionary keyed by the parts of the partition, with the updated tallies of the
                "field" attribute of nodes in each part.
        """
        parent = partition.parent
        assert parent is not None

        old_tally = parent[self.alias]
        new_tally = dict(old_tally)

        graph = partition.graph

        for part, flow in flows_from_changes(parent, partition).items():
            out_flow = compute_out_flow(graph, self.fields, flow)
            in_flow = compute_in_flow(graph, self.fields, flow)
            new_tally[part] = old_tally[part] - out_flow + in_flow

        return new_tally

    def _get_tally_from_node(self, partition: Partition, node: Hashable) -> float:
        return sum(partition.graph.node_data(node)[field] for field in self.fields)


def compute_out_flow(
    graph: Graph | FrozenGraph, fields: list[str], flow: dict[str, set[Hashable]]
) -> float:
    """Return sum of the "field" attribute of nodes in the "out" set of the flow.

    Args:
        graph (Graph): The graph that the partition is defined on.
        fields (list[str]): The list of node attributes that you want to tally.
        flow (dict): A dictionary containing the flow from the parent of this partition to this
            partition. This dictionary is of the form `{part: {'in': <set of nodes that flowed in>,
            'out': <set of nodes that flowed out>}}`.

    Returns:
        float: The sum of the "field" attribute of nodes in the "out" set of the flow.
    """
    return sum(graph.node_data(node)[field] for node in flow["out"] for field in fields)


def compute_in_flow(
    graph: Graph | FrozenGraph, fields: list[str], flow: dict[str, set[Hashable]]
) -> float:
    """Return sum of the "field" attribute of nodes in the "in" set of the flow.

    Args:
        graph (Graph): The graph that the partition is defined on.
        fields (list[str]): The list of node attributes that you want to tally.
        flow (dict): A dictionary containing the flow from the parent of this partition to this
            partition. This dictionary is of the form `{part: {'in': <set of nodes that flowed in>,
            'out': <set of nodes that flowed out>}}`.

    Returns:
        float: The sum of the "field" attribute of nodes in the "in" set of the flow.
    """
    return sum(graph.node_data(node)[field] for node in flow["in"] for field in fields)
