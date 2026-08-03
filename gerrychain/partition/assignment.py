from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping
from typing import TypeVar, cast

import numpy
import pandas

from .._deprecated import deprecated_parameters
from ..graph import FrozenGraph, Graph

NodeT = TypeVar("NodeT", bound=Hashable)
PartT = TypeVar("PartT", bound=Hashable)


class Assignment(Mapping[Hashable, Hashable]):
    """
    An assignment of nodes into parts.

    The goal of Assignment is to provide an interface that mirrors a
    dictionary (what we have been using for assigning nodes to districts) while making it
    convenient/cheap to access the set of nodes in each part.

    An Assignment has a ``parts`` property that is a dictionary of the form
    ``{part: <frozenset of nodes in part>}``.
    """

    __slots__ = ["parts", "mapping"]
    parts: dict[Hashable, frozenset[Hashable]]
    mapping: dict[Hashable, Hashable]

    def __init__(
        self,
        parts: Mapping[PartT, frozenset[NodeT]],
        mapping: Mapping[NodeT, PartT] | None = None,
        validate: bool = True,
    ) -> None:
        """Initialize a Assignment instance.

        Args:
            parts (dict): Dictionary mapping partition assignments frozensets of nodes.
            mapping (dict | None, optional): Dictionary mapping nodes to partition assignments.
                Default is None.
            validate (bool, optional): Whether to validate the assignment. Default is True.

        Raises:
            ValueError: if the keys of ``parts`` are not unique
            TypeError: if the values of ``parts`` are not frozensets
        """

        if validate:
            number_of_keys = sum(len(keys) for keys in parts.values())
            number_of_unique_keys = len(set().union(*parts.values()))
            if number_of_keys != number_of_unique_keys:
                raise ValueError("Keys must have unique assignments.")
            if not all(isinstance(keys, frozenset) for keys in parts.values()):
                raise TypeError("Level sets must be frozensets")
        self.parts: dict[Hashable, frozenset[Hashable]] = {
            part: frozenset(nodes) for part, nodes in parts.items()
        }

        if not mapping:
            self.mapping: dict[Hashable, Hashable] = {}
            for part, nodes in self.parts.items():
                for node in nodes:
                    self.mapping[node] = part
        else:
            self.mapping = {node: part for node, part in mapping.items()}

    def __repr__(self) -> str:
        return f"<Assignment [{len(self)} keys, {len(self.parts)} parts]>"

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self.mapping)

    def __len__(self) -> int:
        return sum(len(keys) for keys in self.parts.values())

    def __getitem__(self, node: Hashable) -> Hashable:
        return self.mapping[node]

    def copy(self) -> Assignment:
        """Returns a copy of the assignment.

        Does not duplicate the frozensets of nodes, just the parts dictionary.

        Returns:
            Assignment: A copy of the assignment.
        """
        return Assignment(self.parts.copy(), self.mapping.copy(), validate=False)

    def update_flows(self, flows: dict[Hashable, dict[str, set[Hashable]]]) -> None:
        """Update the assignment for some nodes using the given flows.

        This method updates the assignment for some nodes using the given flows. The arguments
        below describe the relevant inputs and behavior.


        Args:
            flows (dict): A dictionary mapping partition assignments to dictionaries with "in" and
                "out" keys, where the value of "in" is a set of nodes flowing into the partition
                and the value of "out" is a set of nodes flowing out of the partition.
        """
        # frm: Update the assignment of nodes to partitions by adding
        #       all of the new nodes and removing all of the old nodes
        #       as represented in the flows (dict keyed by district (part)
        #       of nodes flowing "in" and "out" for that district).
        #
        #       Also, reset the mapping of node to partition (self.mapping)
        #       to reassign each node to its new partition.
        #
        for part, flow in flows.items():
            # Union between frozenset and set returns an object whose type
            # matches the object on the left, which here is a frozenset
            self.parts[part] = (self.parts[part] - flow["out"]) | flow["in"]

            for node in flow["in"]:
                self.mapping[node] = part

    def update_parts(self, new_parts: Mapping[Hashable, Iterable[Hashable]]) -> None:
        """Update some parts of the assignment.

        Args:
            new_parts (dict): dictionary mapping (some) parts to their new sets or frozensets of
                nodes

        """
        for part, nodes in new_parts.items():
            self.parts[part] = frozenset(nodes)

            for node in nodes:
                self.mapping[node] = part

    def to_series(self) -> pandas.Series:
        """Convert to series.

        Returns:
            pandas.Series: The assignment as a Series.
        """
        groups = [pandas.Series(data=part, index=nodes) for part, nodes in self.parts.items()]
        return pandas.concat(groups)

    def to_vector(self) -> numpy.ndarray:
        """Return the assignment as an array of part labels indexed by node id.

        Requires the nodes to be the contiguous integers ``0..n-1``, which is true for the internal
        node ids of a rustworkx-based graph. String part labels are returned as an object array so
        that labels later written into a copy cannot be silently truncated to a fixed width.

        Returns:
            numpy.ndarray: Array of length ``n`` whose ``i``-th entry is the part of node ``i``.

        Raises:
            ValueError: If the nodes are not the contiguous integers ``0..n-1``.
        """
        try:
            vector = numpy.array([self.mapping[node] for node in range(len(self.mapping))])
        except KeyError:
            raise ValueError(
                "to_vector requires the assignment's nodes to be the contiguous integers "
                "0..n-1 (the internal node ids of a rustworkx-based graph)"
            ) from None
        if vector.dtype.kind in "US":
            vector = vector.astype(object)
        return vector

    def to_dict(self) -> dict[Hashable, Hashable]:
        """Convert to dict.

        Returns:
            dict: The assignment as a ``{node: part}`` dictionary.
        """
        return self.mapping

    @classmethod
    @deprecated_parameters(renamed={"assignment": "nodes_to_parts"})
    def from_dict(cls, nodes_to_parts: Mapping[NodeT, PartT] | pandas.Series) -> Assignment:
        """Create an Assignment from a dictionary.

        Args:
            nodes_to_parts (Mapping[Hashable, Hashable] | pandas.Series): mapping (a dict-like
                or a ``pandas.Series``) from nodes to partition assignments

        Returns:
            Assignment: A new instance of Assignment with the same assignments as the
                passed-in dictionary.
        """

        if isinstance(nodes_to_parts, pandas.Series):
            raw_mapping = nodes_to_parts.to_dict()
            if not all(
                isinstance(node, Hashable) and isinstance(part, Hashable)
                for node, part in raw_mapping.items()
            ):
                raise TypeError("Assignment keys and part labels must be hashable")
            return cls.from_dict(cast(dict[Hashable, Hashable], raw_mapping))

        mapping = dict(nodes_to_parts)
        parts = {part: frozenset(keys) for part, keys in level_sets(mapping).items()}
        return cls(parts, mapping)

    def new_assignment_convert_old_node_ids_to_new_node_ids(
        self, node_id_mapping: Mapping[Hashable, Hashable]
    ) -> Assignment:
        """Create a new Assignment object from the one passed in, where the node_ids are changed.

        Create a new Assignment object from the one passed in, where the node_ids are changed
        according to the node_id_mapping from old node_ids to new node_ids.

        This routine was motivated by the fact that node_ids are changed when converting from an
        NetworkX based graph to a RustworkX based graph. An Assignment based on the node_ids in the
        NetworkX based graph would need to be changed to use the new node_ids - the new Asignment
        would be semantically equivalent - just converted to use the new node_ids in the RX based
        graph.

        The node_id_mapping is of the form {old_node_id: new_node_id}"""

        # Dict of the form: {node_id: part_id}
        old_assignment_mapping = self.mapping

        # convert old_node_ids to new_node_ids, keeping part IDs the same
        new_assignment_mapping = {
            node_id_mapping[old_node_id]: part
            for old_node_id, part in old_assignment_mapping.items()
        }
        # Now upate the parts dict that has a frozenset of all the nodes in each part (district)
        new_parts: dict[Hashable, set[Hashable]] = {}
        for cur_node_id, cur_part in new_assignment_mapping.items():
            if cur_part not in new_parts:
                new_parts[cur_part] = set()
            new_parts[cur_part].add(cur_node_id)
        frozen_parts = {part: frozenset(nodes) for part, nodes in new_parts.items()}
        new_assignment = Assignment(frozen_parts, new_assignment_mapping)

        return new_assignment


def get_assignment(
    part_assignment: str | Mapping[NodeT, PartT] | pandas.Series | Assignment,
    graph: Graph | FrozenGraph | None = None,
) -> Assignment:
    """Either extracts an Assignment object from the input graph using the provided key or
    attempts to convert part_assignment into an Assignment object.

    Args:
        part_assignment (str | Mapping[NodeT, PartT] | pandas.Series | Assignment): A node
            attribute key, mapping, pandas Series, or Assignment object.
        graph (Graph | FrozenGraph | None, optional): The graph from which to extract the
            assignment. Defaults to None.

    Returns:
        Assignment: An Assignment object containing the assignment corresponding to the
            part_assignment input

    Raises:
        TypeError: If the part_assignment is a string and the graph
            is not provided.
        TypeError: If the part_assignment is not a string or dictionary.
    """
    if isinstance(part_assignment, str):
        # Extract an assignment using the named node attribute
        if graph is None:
            raise TypeError(
                "You must provide a graph when using a node attribute for the part_assignment"
            )
        return Assignment.from_dict(
            {node: graph.node_data(node)[part_assignment] for node in graph}
        )
    if isinstance(part_assignment, Assignment):
        return part_assignment
    if isinstance(part_assignment, pandas.Series):
        return Assignment.from_dict(part_assignment)
    if isinstance(part_assignment, Mapping):
        return Assignment.from_dict(part_assignment)
    raise TypeError("Assignment must be a mapping or a node attribute key")


@deprecated_parameters(renamed={"container": "container_fn"})
def level_sets(
    mapping: Mapping[NodeT, PartT],
    container_fn: Callable[[], set[NodeT]] = set,
) -> defaultdict[PartT, set[NodeT]]:
    """Inverts a dictionary.

    ``{key: value}`` becomes ``{value: <container of keys that map to value>}``.

    Args:
        mapping (dict): A dictionary to invert. Keys and values can be of any type.
        container_fn (Callable[[], set], optional): A zero-argument callable returning a container
            used to collect keys that map to the same value. By default, this is ``set``.

    Returns:
        DefaultDict: A dictionary where each key is a value from the original dictionary, and the
            corresponding value is a container (by default, a set) of keys from the original
            dictionary that mapped to this value.
    Example usage::

    .. code_block:: python

        >>> level_sets({'a': 1, 'b': 1, 'c': 2})
        defaultdict(<class 'set'>, {1: {'a', 'b'}, 2: {'c'}})
    """
    sets: defaultdict[PartT, set[NodeT]] = defaultdict(container_fn)
    for source, target in mapping.items():
        sets[target].add(source)
    return sets
