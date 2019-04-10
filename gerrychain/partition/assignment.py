from collections import defaultdict
from itertools import chain, repeat
from collections.abc import Mapping

import pandas

from ..updaters.flows import flows_from_changes


class Assignment(Mapping):
    """An assignment of nodes into parts.

    The goal of :class:`Assignment` is to provide an interface that mirrors a
    dictionary (what we have been using for assigning nodes to districts) while making it
    convenient/cheap to access the set of nodes in each part.

    An :class:`Assignment` has a ``parts`` property that is a dictionary of the form
    ``{part: <frozenset of nodes in part>}``.
    """

    def __init__(self, parts, validate=True):
        if validate:
            number_of_keys = sum(len(keys) for keys in parts.values())
            number_of_unique_keys = len(set().union(*parts.values()))
            if number_of_keys != number_of_unique_keys:
                raise ValueError("Keys must have unique assignments.")
            if not all(isinstance(keys, frozenset) for keys in parts.values()):
                raise TypeError("Level sets must be frozensets")
        self.parts = parts

    def __repr__(self):
        return "<Assignment [{} keys, {} parts]>".format(len(self), len(self.parts))

    def __iter__(self):
        return self.keys()

    def __len__(self):
        return sum(len(keys) for keys in self.parts.values())

    def __getitem__(self, node):
        for part, nodes in self.parts.items():
            if node in nodes:
                return part
        raise KeyError(node)

    def copy(self):
        """Returns a copy of the assignment.
        Does not duplicate the frozensets of nodes, just the parts dictionary.
        """
        return Assignment(self.parts.copy(), validate=False)

    def update(self, mapping):
        """Update the assignment for some nodes using the given mapping.
        """
        flows = flows_from_changes(self, mapping)
        for part, flow in flows.items():
            # Union between frozenset and set returns an object whose type
            # matches the object on the left, which here is a frozenset
            self.parts[part] = (self.parts[part] - flow["out"]) | flow["in"]

    def items(self):
        """Iterate over ``(node, part)`` tuples, where ``node`` is assigned to ``part``.
        """
        for part, nodes in self.parts.items():
            for node in nodes:
                yield (node, part)

    def keys(self):
        return chain(*self.parts.values())

    def values(self):
        return chain(
            *(repeat(value, times=len(keys)) for value, keys in self.parts.items())
        )

    def update_parts(self, new_parts):
        """Update some parts of the assignment. Does not check that every node is
        still assigned to a part.

        :param dict new_parts: dictionary mapping (some) parts to their new sets or
            frozensets of nodes
        """
        for part, nodes in new_parts.items():
            self.parts[part] = frozenset(nodes)

    def to_series(self):
        """Convert the assignment to a :class:`pandas.Series`."""
        groups = [
            pandas.Series(data=part, index=nodes) for part, nodes in self.parts.items()
        ]
        return pandas.concat(groups)

    def to_dict(self):
        """Convert the assignment to a ``{node: part}`` dictionary.
        This is expensive and should be used rarely."""
        return {node: part for part, nodes in self.parts.items() for node in nodes}

    @classmethod
    def from_dict(cls, assignment):
        """Create an :class:`Assignment` from a dictionary. This is probably the method you want
        to use to create a new assignment.

        This also works for :class:`pandas.Series`.
        """
        parts = {part: frozenset(keys) for part, keys in level_sets(assignment).items()}

        return cls(parts)


def get_assignment(assignment, graph=None):
    if isinstance(assignment, str):
        if graph is None:
            raise TypeError(
                "You must provide a graph when using a node attribute for the assignment"
            )
        return Assignment.from_dict(
            {node: graph.nodes[node][assignment] for node in graph}
        )
    elif callable(getattr(assignment, "items", None)):
        return Assignment.from_dict(assignment)
    elif isinstance(assignment, Assignment):
        return assignment
    else:
        raise TypeError("Assignment must be a dict or a node attribute key")


def level_sets(mapping: dict, container=set):
    """Inverts a dictionary. ``{key: value}`` becomes
    ``{value: <container of keys that map to value>}``."""
    sets = defaultdict(container)
    for source, target in mapping.items():
        sets[target].add(source)
    return sets
