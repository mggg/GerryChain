from ..utils import level_sets
from .updaters.flows import flows_from_changes


class Assignment:
    def __init__(self, parts):
        self.parts = parts

    @classmethod
    def from_dict(cls, assignment: dict):
        parts = {
            part: frozenset(nodes) for part, nodes in level_sets(assignment).items()
        }
        return cls(parts)

    def __getitem__(self, node):
        for part, nodes in self.parts.items():
            if node in nodes:
                return part
        raise KeyError(node)

    def copy(self):
        # This .copy() does not duplicate the frozensets
        return Assignment(self.parts.copy())

    def update(self, mapping: dict):
        flows = flows_from_changes(self, mapping)
        for part, flow in flows.items():
            # Union between frozenset and set returns an object whose type
            # matches the object on the left, which here is a frozenset
            self.parts[part] = (self.parts[part] - flow["out"]) | flow["in"]

    def items(self):
        for part, nodes in self.parts.items():
            for node in nodes:
                yield (node, part)

    def update_parts(self, new_parts):
        for part, nodes in new_parts.items():
            self.parts[part] = frozenset(nodes)


def get_assignment(assignment, graph):
    if isinstance(assignment, str):
        return Assignment.from_dict(graph.node_attribute(assignment))
    elif isinstance(assignment, dict):
        return Assignment.from_dict(assignment)
    elif isinstance(assignment, Assignment):
        return assignment
    else:
        raise TypeError("Assignment must be a dict or a node attribute key")
