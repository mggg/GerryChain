from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Iterator, Mapping

import pandas

from ..graph import Graph


class Assignment(Mapping):
    """
    An assignment of nodes into parts.

    The goal of Assignment is to provide an interface that mirrors a
    dictionary (what we have been using for assigning nodes to districts) while making it
    convenient/cheap to access the set of nodes in each part.

    An Assignment has a ``parts`` property that is a dictionary of the form
    ``{part: <frozenset of nodes in part>}``.
    """

    __slots__ = ["parts", "mapping"]

    def __init__(self, parts: dict, mapping: dict | None = None, validate: bool = True) -> None:
        """Initialize a Assignment instance.

        Args:
            parts (Dict): Dictionary mapping partition assignments frozensets of nodes.
            mapping (Optional[Dict], optional): Dictionary mapping nodes to partition assignments.
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
        self.parts = parts

        if not mapping:
            self.mapping = {}
            for part, nodes in self.parts.items():
                for node in nodes:
                    self.mapping[node] = part
        else:
            self.mapping = mapping

    def __repr__(self) -> str:
        return f"<Assignment [{len(self)} keys, {len(self.parts)} parts]>"

    def __iter__(self) -> Iterator[Hashable]:
        return self.keys()

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
            flows (Dict): A dictionary mapping partition assignments to dictionaries with "in" and
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

    def items(self) -> Iterator[tuple[Hashable, Hashable]]:
        """Iterate over ``(node, part)`` tuples, where ``node`` is assigned to ``part``."""
        yield from self.mapping.items()

    def keys(self) -> Iterator[Hashable]:
        yield from self.mapping.keys()

    def values(self) -> Iterator[Hashable]:
        yield from self.mapping.values()

    def update_parts(self, new_parts: dict) -> None:
        """Update some parts of the assignment.

        Args:
            new_parts (Dict): dictionary mapping (some) parts to their new sets or frozensets of
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

    def to_dict(self) -> dict:
        """Convert to dict.

        Returns:
            Dict: The assignment as a ``{node: part}`` dictionary.
        """
        return self.mapping

    @classmethod
    def from_dict(cls, nodes_to_parts: dict) -> Assignment:
        """Create an Assignment from a dictionary.

        Args:
            nodes_to_parts (Dict): dictionary mapping nodes to partition assignments

        Returns:
            Assignment: A new instance of Assignment with the same assignments as the
                passed-in dictionary.
        """

        parts = {part: frozenset(keys) for part, keys in level_sets(nodes_to_parts).items()}

        # frm: TODO: Refactoring: Peter: from_dict() has issues with pandas series instead of a dict...
        #
        # I looked at this code and realized that the constructor for an Assignment
        # allows for passing in a dict mapping nodes to parts, which is what we
        # have in-hand in the nodes_to_parts parameter.  However, when I passed
        # nodes_to_parts to the Assignment constructor, I ended up with test failures
        # because the tests passed in a pandas series for nodes_to_parts instead
        # of an actual dict.
        #
        #     def test_assignment_can_be_instantiated_from_series(self):
        #         series = pandas.Series([1, 2, 1, 2], index=[1, 2, 3, 4])
        #         assignment = Assignment.from_dict(series)
        #         assert assignment == {1: 1, 2: 2, 3: 1, 4: 2}
        #
        # There is a pandas function that converts a series to a dict, so I could just
        # change the test (test_assignment.py) to do this conversion before passing
        # it in, but perhaps there is a good reason (legacy?) for allowing nodes_to_parts
        # to be a pandas series.  If so, then we could just change the type hint to
        # allow pandas series and do the conversion inside from_dict() before passing
        # it on to the Assignment constructor.
        #
        # Note that if we left the code as-is, it all works because the Assignment
        # constructor just rebuilds the nodes_to_parts dict if one is not supplied...
        #
        # What would you prefer?

        return cls(
            parts
            # ,               # Commented out because __init__() croaks if the nodes_to_parts
            # nodes_to_parts  # is a pandas series instead of a dict...
        )

    def new_assignment_convert_old_node_ids_to_new_node_ids(
        self, node_id_mapping: dict
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
        new_parts = {}
        for cur_node_id, cur_part in new_assignment_mapping.items():
            if cur_part not in new_parts:
                new_parts[cur_part] = set()
            new_parts[cur_part].add(cur_node_id)
        for cur_part, set_of_nodes in new_parts.items():
            new_parts[cur_part] = frozenset(set_of_nodes)

        #  pandas.Series(data=part, index=nodes) for part, nodes in self.parts.items()

        new_assignment = Assignment(new_parts, new_assignment_mapping)

        return new_assignment


def get_assignment(
    part_assignment: str | dict | Assignment, graph: Graph | None = None
) -> Assignment:
    """Either extracts an Assignment object from the input graph using the provided key or
    attempts to convert part_assignment into an Assignment object.

    Args:
        part_assignment (str): A node attribute key, dictionary, or Assignment object
            corresponding to the desired assignment.
        graph (Optional[Graph], optional): The graph from which to extract the assignment. Default
            is None.

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
    # Check if assignment is a dict or a mapping type
    elif callable(getattr(part_assignment, "items", None)):
        return Assignment.from_dict(part_assignment)
    elif isinstance(part_assignment, Assignment):
        return part_assignment
    else:
        raise TypeError("Assignment must be a dict or a node attribute key")


def level_sets(mapping: dict, container: type[set] = set) -> defaultdict:
    """Inverts a dictionary.

    ``{key: value}`` becomes ``{value: <container of keys that map to value>}``.

    Args:
        mapping (Dict): A dictionary to invert. Keys and values can be of any type.
        container (Type[Set], optional): A container type used to collect keys that map to the same
            value. By default, the container type is ``set``.

    Returns:
        DefaultDict: A dictionary where each key is a value from the original dictionary, and the
            corresponding value is a container (by default, a set) of keys from the original
            dictionary that mapped to this value.
    Example usage::

    .. code_block:: python

        >>> level_sets({'a': 1, 'b': 1, 'c': 2})
        defaultdict(<class 'set'>, {1: {'a', 'b'}, 2: {'c'}})
    """
    sets: dict = defaultdict(container)
    for source, target in mapping.items():
        sets[target].add(source)
    return sets
