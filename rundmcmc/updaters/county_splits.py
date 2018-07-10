import collections
from enum import Enum

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
