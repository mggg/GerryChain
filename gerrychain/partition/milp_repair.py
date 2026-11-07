"""Frozen-core mixed-integer repair for small/local initial partitions.

This module is experimental.  It uses :func:`scipy.optimize.milp` to optimize
assignment of a locally selected movable shell while single-commodity flows
certify connection to each district's retained core.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from ..graph import FrozenGraph, Graph
from .assignment import Assignment
from .assignment_repair import (
    AssignmentRepairError,
    AssignmentRepairInfeasible,
    AssignmentRepairSearchExhausted,
    _coerce_assignment,
    _components_for_nodes,
    _node_populations,
    _part_order,
    _within_bounds,
    validate_repaired_assignment,
)

GraphLike = Graph | FrozenGraph


@dataclass(frozen=True)
class MILPAssignmentRepairResult:
    """Audited result of a frozen-core border-shell MILP repair."""

    assignment: dict[Hashable, Hashable]
    populations_before: dict[Hashable, float]
    populations_after: dict[Hashable, float]
    changed_nodes: frozenset[Hashable]
    population_moved: float
    nodes_moved: int
    shell_size: int
    border_rings: int
    optimal_within_model: bool
    solver_status: int


def _shell_and_anchors(
    graph: GraphLike,
    mapping: Mapping[Hashable, Hashable],
    populations: Mapping[Hashable, float],
    border_rings: int = 1,
) -> tuple[set[Hashable], dict[Hashable, set[Hashable]], set[Hashable]]:
    node_rank = {node: i for i, node in enumerate(graph.nodes)}
    parts = _part_order(graph, mapping)
    by_part = {part: {node for node in graph.nodes if mapping[node] == part} for part in parts}
    cores: dict[Hashable, set[Hashable]] = {}
    fragments: set[Hashable] = set()
    source_parts: set[Hashable] = set()
    affected: set[Hashable] = set()
    for part, nodes in by_part.items():
        components = _components_for_nodes(graph, nodes, node_rank)
        core = max(components, key=lambda c: (sum(populations[n] for n in c), -min(node_rank[n] for n in c)))
        cores[part] = set(core)
        if len(components) > 1:
            affected.add(part)
            source_parts.add(part)
            for component in components:
                if component != core:
                    fragments.update(component)

    # Include districts reached by a fragment, since their boundary may need to
    # donate population, and include both sides of affected district boundaries.
    for node in fragments:
        affected.update(mapping[neighbor] for neighbor in graph.neighbors(node) if mapping[neighbor] != mapping[node])
    shell = set(fragments)
    for part in affected - source_parts:
        for node in cores[part]:
            if any(mapping[neighbor] != part and mapping[neighbor] in affected for neighbor in graph.neighbors(node)):
                shell.add(node)

    for _ in range(border_rings):
        shell.update(
            node
            for part in affected
            for node in cores[part]
            if node not in shell
            and any(neighbor in shell for neighbor in graph.neighbors(node))
        )

    anchors: dict[Hashable, set[Hashable]] = {}
    for part in affected:
        remaining = cores[part] - shell
        if not remaining:
            # Keep one highest-population core node as a root when every core
            # node lies on the selected boundary. The shell remains local, but
            # the model must have a nonempty anchor for flow connectivity.
            anchor_node = max(cores[part], key=lambda node: (populations[node], -node_rank[node]))
            shell.remove(anchor_node)
            remaining = {anchor_node}
        components = _components_for_nodes(graph, remaining, node_rank)
        anchor = max(components, key=lambda c: (sum(populations[n] for n in c), -min(node_rank[n] for n in c)))
        anchors[part] = set(anchor)
        for component in components:
            if component != anchor:
                shell.update(component)

    return shell, anchors, affected


def repair_assignment_milp(
    graph: GraphLike,
    assignment: str | Mapping[Hashable, Hashable] | Assignment,
    pop_col: str,
    pop_target: float | int,
    epsilon: float,
    *,
    border_rings: int = 1,
    max_shell_nodes: int | None = None,
    time_limit: float | None = None,
) -> MILPAssignmentRepairResult:
    """Solve the frozen-core/border-shell repair model.

    The returned result is exact for the generated shell, permitted labels,
    population bounds, and flow connectivity formulation. The shell is the
    disconnected fragments plus border VTDs, optionally expanded by
    ``border_rings``.
    """

    if pop_target <= 0 or epsilon < 0:
        raise ValueError("pop_target must be positive and epsilon non-negative.")
    if border_rings < 0:
        raise ValueError("border_rings must be non-negative.")
    if max_shell_nodes is not None and max_shell_nodes <= 0:
        raise ValueError("max_shell_nodes must be positive when provided.")
    if time_limit is not None and time_limit <= 0:
        raise ValueError("time_limit must be positive when provided.")
    original = _coerce_assignment(graph, assignment)
    parts = _part_order(graph, original)
    node_pop = _node_populations(graph, pop_col)
    if not all(float(value).is_integer() for value in node_pop.values()):
        raise AssignmentRepairError("MILP repair requires integer node populations.")
    before = {part: sum(node_pop[n] for n in graph.nodes if original[n] == part) for part in parts}
    lower = float(pop_target) * (1 - epsilon)
    upper = float(pop_target) * (1 + epsilon)
    if any(not _within_bounds(value, lower, upper) for value in before.values()):
        raise AssignmentRepairError("The input assignment must satisfy the population range.")

    shell, anchors, affected = _shell_and_anchors(graph, original, node_pop, border_rings)
    if max_shell_nodes is not None and len(shell) > max_shell_nodes:
        raise AssignmentRepairSearchExhausted(
            f"MILP shell has {len(shell)} nodes, exceeding max_shell_nodes={max_shell_nodes}."
        )
    if not shell:
        populations = validate_repaired_assignment(graph, original, pop_col, pop_target, epsilon)
        return MILPAssignmentRepairResult(
            assignment=original,
            populations_before=before,
            populations_after=populations,
            changed_nodes=frozenset(),
            population_moved=0.0,
            nodes_moved=0,
            shell_size=0,
            border_rings=border_rings,
            optimal_within_model=True,
            solver_status=0,
        )
    shell_nodes = tuple(node for node in graph.nodes if node in shell)
    shell_set = set(shell_nodes)
    allowed: dict[Hashable, tuple[Hashable, ...]] = {}
    for node in shell_nodes:
        labels = {original[node]}
        labels.update(original[neighbor] for neighbor in graph.neighbors(node))
        allowed[node] = tuple(part for part in parts if part in labels and (part in affected or part == original[node]))

    x_keys = [(node, part) for node in shell_nodes for part in allowed[node]]
    x_index = {key: i for i, key in enumerate(x_keys)}
    flow_keys: list[tuple[Hashable, Hashable, Hashable]] = []
    flow_districts = tuple(anchors)
    # Use graph order to make one directed pair per undirected edge for
    # arbitrary hashable node labels.
    node_rank = {node: i for i, node in enumerate(graph.nodes)}
    for district in flow_districts:
        relevant = set(shell_nodes).union(anchors[district])
        for node in relevant:
            for neighbor in graph.neighbors(node):
                if neighbor in relevant and node_rank[node] < node_rank[neighbor]:
                    flow_keys.extend(((district, node, neighbor), (district, neighbor, node)))

    anchor_root_keys = [(district, node) for district in flow_districts for node in anchors[district]]
    anchor_root_index = {key: i for i, key in enumerate(anchor_root_keys)}
    flow_index = {key: i for i, key in enumerate(flow_keys)}
    keys_count = len(x_keys) + len(flow_keys) + len(anchor_root_keys)
    x_offset = 0
    flow_offset = len(x_keys)
    anchor_root_offset = flow_offset + len(flow_keys)
    n_x = len(x_keys)
    rows: list[tuple[dict[int, float], float, float]] = []

    for node in shell_nodes:
        rows.append(({x_offset + x_index[(node, part)]: 1.0 for part in allowed[node]}, 1.0, 1.0))

    for part in parts:
        coefficients: dict[int, float] = {}
        for node in shell_nodes:
            if part in allowed[node]:
                coefficients[x_offset + x_index[(node, part)]] = node_pop[node]
        fixed = before[part] - sum(node_pop[node] for node in shell_nodes if original[node] == part)
        rows.append((coefficients, lower - fixed, upper - fixed))

    big_m = float(len(shell_nodes) + 1)
    for district in flow_districts:
        for node in shell_nodes:
            coefficients: dict[int, float] = {}
            for key, i in flow_index.items():
                if key[0] != district:
                    continue
                if key[2] == node:
                    coefficients[flow_offset + i] = coefficients.get(flow_offset + i, 0.0) + 1.0
                if key[1] == node:
                    coefficients[flow_offset + i] = coefficients.get(flow_offset + i, 0.0) - 1.0
            if (node, district) in x_index:
                coefficients[x_offset + x_index[(node, district)]] = -1.0
            rows.append((coefficients, 0.0, 0.0))

        root_balance: dict[int, float] = {}
        for key, i in anchor_root_index.items():
            if key[0] == district:
                root_balance[anchor_root_offset + i] = 1.0
        for node in shell_nodes:
            if (node, district) in x_index:
                root_balance[x_offset + x_index[(node, district)]] = -1.0
        rows.append((root_balance, 0.0, 0.0))

    for key in flow_keys:
        district, source, destination = key
        flow_column = flow_offset + flow_index[key]
        if source in shell_set and (source, district) in x_index:
            rows.append((
                {flow_column: 1.0, x_offset + x_index[(source, district)]: -big_m},
                -np.inf,
                0.0,
            ))
        if destination in shell_set and (destination, district) in x_index:
            rows.append((
                {flow_column: 1.0, x_offset + x_index[(destination, district)]: -big_m},
                -np.inf,
                0.0,
            ))

    matrix = lil_matrix((len(rows), keys_count))
    row_lower = np.empty(len(rows))
    row_upper = np.empty(len(rows))
    for row, (coefficients, lo, hi) in enumerate(rows):
        for column, value in coefficients.items():
            matrix[row, column] = value
        row_lower[row] = lo
        row_upper[row] = hi

    objective = np.zeros(keys_count)
    for node, part in x_keys:
        if original[node] != part:
            objective[x_offset + x_index[(node, part)]] = node_pop[node] * big_m + 1.0
    options = {"mip_rel_gap": 0.0}
    if time_limit is not None:
        options["time_limit"] = time_limit
    result = milp(
        c=objective,
        integrality=np.array(
            [1.0] * n_x
            + [0.0] * (len(flow_keys) + len(anchor_root_keys))
        ),
        bounds=Bounds(
            np.zeros(keys_count),
            np.r_[
                np.ones(n_x),
                np.full(len(flow_keys) + len(anchor_root_keys), big_m),
            ],
        ),
        constraints=LinearConstraint(matrix.tocsr(), row_lower, row_upper),
        options=options,
    )
    if not result.success:
        if result.status == 2:
            raise AssignmentRepairInfeasible(f"MILP repair failed: {result.message}")
        raise AssignmentRepairSearchExhausted(
            f"MILP solver did not establish feasibility or optimality: {result.message}"
        )
    repaired = dict(original)
    for node, part in x_keys:
        if result.x[x_offset + x_index[(node, part)]] > 0.5:
            repaired[node] = part
    try:
        populations_after = validate_repaired_assignment(graph, repaired, pop_col, pop_target, epsilon)
    except AssignmentRepairError as error:
        raise AssignmentRepairError(f"MILP assignment {repaired!r} failed validation: {error}") from error
    changed_nodes = frozenset(node for node in graph.nodes if repaired[node] != original[node])
    return MILPAssignmentRepairResult(
        assignment=repaired,
        populations_before=before,
        populations_after=populations_after,
        changed_nodes=changed_nodes,
        population_moved=sum(node_pop[node] for node in changed_nodes),
        nodes_moved=len(changed_nodes),
        shell_size=len(shell_nodes),
        border_rings=border_rings,
        optimal_within_model=True,
        solver_status=int(result.status),
    )
