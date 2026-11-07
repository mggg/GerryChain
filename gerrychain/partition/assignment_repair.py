"""Validation primitives for graph-based initial-assignment repair."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Hashable, Mapping

from ..graph import FrozenGraph, Graph
from .assignment import Assignment, get_assignment

GraphLike = Graph | FrozenGraph


class AssignmentRepairError(ValueError):
    """Base error for invalid or unrepairable initial assignments."""


class AssignmentRepairInfeasible(AssignmentRepairError):
    """The configured local repair model has no valid solution."""


class AssignmentRepairSearchExhausted(AssignmentRepairError):
    """A configured solver or search limit prevented a conclusion."""


def _coerce_assignment(
    graph: GraphLike,
    assignment: str | Mapping[Hashable, Hashable] | Assignment,
) -> dict[Hashable, Hashable]:
    mapping = dict(get_assignment(assignment, graph).mapping)
    graph_nodes = set(graph.node_indices)
    if set(mapping) != graph_nodes:
        raise AssignmentRepairError("Assignment nodes must match graph nodes exactly.")
    if not mapping:
        raise AssignmentRepairError("Cannot repair an empty assignment.")
    return mapping


def _part_order(graph: GraphLike, mapping: Mapping[Hashable, Hashable]) -> tuple[Hashable, ...]:
    return tuple(dict.fromkeys(mapping[node] for node in graph.nodes))


def _components_for_nodes(
    graph: GraphLike, nodes: set[Hashable], node_order: Mapping[Hashable, int]
) -> list[frozenset[Hashable]]:
    unseen = set(nodes)
    components: list[frozenset[Hashable]] = []
    while unseen:
        start = min(unseen, key=node_order.__getitem__)
        unseen.remove(start)
        component = {start}
        queue = deque((start,))
        while queue:
            node = queue.popleft()
            for neighbor in graph.neighbors(node):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        components.append(frozenset(component))
    return components


def _node_populations(graph: GraphLike, pop_col: str) -> dict[Hashable, float]:
    populations: dict[Hashable, float] = {}
    for node in graph.nodes:
        try:
            population = float(graph.node_data(node)[pop_col])
        except (KeyError, TypeError, ValueError) as error:
            raise AssignmentRepairError(
                f"Node {node!r} has no numeric population in {pop_col!r}."
            ) from error
        if not math.isfinite(population) or population < 0:
            raise AssignmentRepairError(f"Node {node!r} has invalid population {population!r}.")
        populations[node] = population
    return populations


def _within_bounds(population: float, lower: float, upper: float) -> bool:
    return lower <= population <= upper


def validate_repaired_assignment(
    graph: GraphLike,
    assignment: str | Mapping[Hashable, Hashable] | Assignment,
    pop_col: str,
    pop_target: float | int,
    epsilon: float,
) -> dict[Hashable, float]:
    """Validate coverage, induced contiguity, and population balance."""

    if pop_target <= 0 or epsilon < 0:
        raise ValueError("pop_target must be positive and epsilon non-negative.")
    mapping = _coerce_assignment(graph, assignment)
    populations = {part: 0.0 for part in _part_order(graph, mapping)}
    node_populations = _node_populations(graph, pop_col)
    nodes_by_part: dict[Hashable, set[Hashable]] = {part: set() for part in populations}
    for node, part in mapping.items():
        populations[part] += node_populations[node]
        nodes_by_part[part].add(node)
    node_order = {node: index for index, node in enumerate(graph.nodes)}
    disconnected = {
        part: _components_for_nodes(graph, nodes, node_order)
        for part, nodes in nodes_by_part.items()
        if len(_components_for_nodes(graph, nodes, node_order)) > 1
    }
    if disconnected:
        raise AssignmentRepairError(
            "Assignment has disconnected parts: " + ", ".join(repr(part) for part in disconnected)
        )
    lower = float(pop_target) * (1 - epsilon)
    upper = float(pop_target) * (1 + epsilon)
    if any(not _within_bounds(population, lower, upper) for population in populations.values()):
        raise AssignmentRepairError(f"Assignment has populations outside [{lower:g}, {upper:g}].")
    return populations
