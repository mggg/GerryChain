import collections
from enum import Enum
from typing import Callable, Dict


CountyInfo = collections.namedtuple("CountyInfo", "split nodes contains")
"""
A named tuple to store county split information.

:param split: The county split status. Makes use of
    :class:`.CountySplit` enum to compute.
:type split: int
:param nodes: The nodes that are contained in the county.
:type nodes: List
:param contains: The assignment IDs that are contained in the county.
:type contains: Set
"""


class CountySplit(Enum):
    """
    Enum to track county splits in a partition.

    :cvar NOT_SPLIT: The county is not split.
    :cvar NEW_SPLIT: The county is split in the current partition.
    :cvar OLD_SPLIT: The county is split in the parent partition.
    """

    NOT_SPLIT = 0
    NEW_SPLIT = 1
    OLD_SPLIT = 2


def county_splits(partition_name: str, county_field_name: str) -> Callable:
    """
    Update that allows for the tracking of county splits.

    :param partition_name: Name that the :class:`.Partition` instance will store.
    :type partition_name: str
    :param county_field_name: Name of county ID field on the graph.
    :type county_field_name: str

    :returns: The tracked data is a dictionary keyed on the county ID. The
              stored values are tuples of the form `(split, nodes, seen)`.
              `split` is a :class:`.CountySplit` enum, `nodes` is a list of
              node IDs, and `seen` is a list of assignment IDs that are
              contained in the county.
    :rtype: Callable
    """

    def _get_county_splits(partition):
        return compute_county_splits(partition, county_field_name, partition_name)

    return _get_county_splits


def compute_county_splits(
    partition, county_field: str, partition_field: str
) -> Dict[str, CountyInfo]:
    """
    Track nodes in counties and information about their splitting.

    :param partition: The partition object to compute county splits for.
    :type partition: :class:`~gerrychain.partition.Partition`
    :param county_field: Name of county ID field on the graph.
    :type county_field: str
    :param partition_field: Name of the attribute in the graph
        that stores the partition information. The county
        split information will be computed with respect to this
        division of the graph.
    :type partition_field: str

    :returns: A dict containing the information on how counties changed
        between the parent and child partitions. If there is no parent
        partition, then only the OLD_SPLIT and NOT_SPLIT values will be
        used.
    :rtype: Dict[str, CountyInfo]
    """

    # Create the initial county data containers.
    if not partition.parent:
        county_dict = dict()

        for node in partition.graph.node_indices:
            county = partition.graph.lookup(node, county_field)
            if county in county_dict:
                split, nodes, seen = county_dict[county]
            else:
                split, nodes, seen = CountySplit.NOT_SPLIT, [], set()

            nodes.append(node)
            seen.update(set([partition.assignment.mapping[node]]))

            if len(seen) > 1:
                split = CountySplit.OLD_SPLIT

            county_dict[county] = CountyInfo(split, nodes, seen)

        return county_dict

    new_county_dict = dict()

    parent = partition.parent
    for county, county_info in parent[partition_field].items():
        seen = set(partition.assignment.mapping[node] for node in county_info.nodes)

        split = CountySplit.NOT_SPLIT

        if len(seen) > 1:
            if county_info.split != CountySplit.OLD_SPLIT:
                split = CountySplit.NEW_SPLIT
            else:
                split = CountySplit.OLD_SPLIT

        new_county_dict[county] = CountyInfo(split, county_info.nodes, seen)

    return new_county_dict


def tally_region_splits(reg_attr_lst):
    """
    A naive updater for tallying the number of times a region attribute is split.
    for each region attribute in reg_attr_lst.

    :param reg_attr_lst: A list of region names to tally splits for.
    :type reg_attr_lst: List[str]

    :returns: A function that takes a partition and returns a dictionary which
        maps the region name to the number of times that it is split in a
        a particular partition.
    :rtype: Callable
    """

    def _get_splits(partition):
        nonlocal reg_attr_lst
        if "cut_edges" not in partition.updaters:
            raise ValueError("The cut_edges updater must be attached to the partition")
        return {
            reg_attr: total_reg_splits(partition, reg_attr) for reg_attr in reg_attr_lst
        }

    return _get_splits


def total_reg_splits(partition, reg_attr):
    """Returns the total number of times that reg_attr is split in the partition."""
    all_region_names = set(
        partition.graph.nodes[node][reg_attr] for node in partition.graph.nodes
    )
    split = {name: 0 for name in all_region_names}
    # Require that the cut_edges updater is attached to the partition
    for node1, node2 in partition["cut_edges"]:
        if (
            partition.assignment[node1] != partition.assignment[node2]
            and partition.graph.nodes[node1][reg_attr]
            == partition.graph.nodes[node2][reg_attr]
        ):
            split[partition.graph.nodes[node1][reg_attr]] += 1
            split[partition.graph.nodes[node2][reg_attr]] += 1

    return sum(1 for value in split.values() if value > 0)
