from __future__ import annotations

import collections
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..partition.partition import Partition

CountyInfo = collections.namedtuple("CountyInfo", "split nodes contains")
"""
A named tuple to store county split information.

Args:
    split (int): The county split status. Makes use of
        :class:`.CountySplit` enum to compute.
    nodes (List): The nodes that are contained in the county.
    contains (Set): The assignment IDs that are contained in the county.
"""


class CountySplit(Enum):
    """
    Enum to track county splits in a partition.

    Attributes:
        NOT_SPLIT (Any): The county is not split.
        NEW_SPLIT (Any): The county is split in the current partition.
        OLD_SPLIT (Any): The county is split in the parent partition.
    """

    NOT_SPLIT = 0
    NEW_SPLIT = 1
    OLD_SPLIT = 2


def county_splits(partition_name: str, county_field_name: str) -> Callable:
    """An updater for tracking the number of counties that are split in a partition.

    Args:
        partition_name (str): Name that the :class:`.Partition` instance will store.
        county_field_name (str): Name of county ID field on the graph.

    Returns:
        Callable: The tracked data is a dictionary keyed on the county ID. The stored values are
            tuples of the form `(split, nodes, seen)`. `split` is a :class:`.CountySplit` enum,
            `nodes` is a list of node IDs, and `seen` is a list of assignment IDs that are
            contained in the county.
    """

    def _get_county_splits(partition: Partition) -> dict[str, CountyInfo]:
        return compute_county_splits(partition, county_field_name, partition_name)

    return _get_county_splits


def compute_county_splits(
    partition: Partition, county_field: str, partition_field: str
) -> dict[str, CountyInfo]:
    """Computes the number of counties that are split in a partition.

    Args:
        partition (:class:`~gerrychain.partition.Partition`): The partition object to compute
            county splits for.
        county_field (str): Name of county ID field on the graph.
        partition_field (str): Name of the attribute in the graph that stores the partition
            information. The county split information will be computed with respect to this
            division of the graph.

    Returns:
        Dict[str, CountyInfo]: A dict containing the information on how counties changed between
            the parent and child partitions. If there is no parent partition, then only the
            OLD_SPLIT and NOT_SPLIT values will be used.
    """

    # Create the initial county data containers.
    if not partition.parent:
        county_dict = dict()

        for node_id in partition.graph.node_indices:
            # First figure get current status of the county's information
            county = partition.graph.node_data(node_id)[county_field]
            if county in county_dict:
                split, nodes, seen = county_dict[county]
            else:
                split, nodes, seen = CountySplit.NOT_SPLIT, [], set()

            # Now update "nodes" and "seen" with this node_id and the part (district) from
            # partition's assignment.
            nodes.append(node_id)
            seen.update(set([partition.assignment.mapping[node_id]]))

            # lastly, if we have "seen" more than one part (district), then the county is split
            # across parts.
            if len(seen) > 1:
                split = CountySplit.OLD_SPLIT

            # update the county_dict with new information
            county_dict[county] = CountyInfo(split, nodes, seen)

        return county_dict

    new_county_dict = dict()

    parent = partition.parent
    for county, county_info in parent[partition_field].items():
        seen = set(partition.assignment.mapping[node_id] for node_id in county_info.nodes)

        split = CountySplit.NOT_SPLIT

        if len(seen) > 1:
            if county_info.split != CountySplit.OLD_SPLIT:
                split = CountySplit.NEW_SPLIT
            else:
                split = CountySplit.OLD_SPLIT

        new_county_dict[county] = CountyInfo(split, county_info.nodes, seen)

    return new_county_dict


def tally_region_splits(reg_attr_lst: list[str]) -> Callable:
    """A naive updater for tallying the number of times a region attribute is split.

    Args:
        reg_attr_lst (List[str]): A list of region names to tally splits for.

    Returns:
        Callable: A function that takes a partition and returns a dictionary which maps the region
            name to the number of times that it is split in a a particular partition.
    """

    def _get_splits(partition: Partition) -> dict[str, int]:
        nonlocal reg_attr_lst
        if "cut_edges" not in partition.updaters:
            raise ValueError("The cut_edges updater must be attached to the partition")
        return {reg_attr: total_reg_splits(partition, reg_attr) for reg_attr in reg_attr_lst}

    return _get_splits


def total_reg_splits(partition: Partition, reg_attr: str) -> int:
    """Computes the total number of times that reg_attr is split in the partition.

    Args:
        partition (Partition): The partition object to compute region splits for.
        reg_attr (str): The name of the region attribute to compute splits for. This should be a
            node attribute on the graph.
    """
    all_region_names = set(
        partition.graph.node_data(node_id)[reg_attr] for node_id in partition.graph.node_indices
    )
    split = {name: 0 for name in all_region_names}
    # Require that the cut_edges updater is attached to the partition
    for node1, node2 in partition["cut_edges"]:
        if (
            partition.assignment[node1] != partition.assignment[node2]
            and partition.graph.node_data(node1)[reg_attr]
            == partition.graph.node_data(node2)[reg_attr]
        ):
            split[partition.graph.node_data(node1)[reg_attr]] += 1
            split[partition.graph.node_data(node2)[reg_attr]] += 1

    return sum(1 for value in split.values() if value > 0)
