import networkx as nx
import pytest

from gerrychain import Graph
from gerrychain.partition.milp_repair import repair_assignment_milp
from gerrychain.partition.assignment_repair import validate_repaired_assignment
from gerrychain.partition.assignment_repair import AssignmentRepairSearchExhausted


def test_milp_repairs_fragment_with_frozen_core_and_border_shell() -> None:
    edges = [(0, 1), (1, 2), (2, 3), (3, 4)]
    populations = {0: 10, 1: 10, 2: 10, 3: 10, 4: 10}
    networkx_graph = nx.Graph(edges)
    nx.set_node_attributes(networkx_graph, populations, "population")
    graph = Graph.from_networkx(networkx_graph)
    source = {0: "A", 1: "A", 2: "B", 3: "B", 4: "A"}

    repaired = repair_assignment_milp(
        graph,
        source,
        pop_col="population",
        pop_target=25,
        epsilon=0.2,
    )

    assert repaired.assignment == {0: "A", 1: "A", 2: "B", 3: "B", 4: "B"}
    assert repaired.population_moved == 10
    assert repaired.nodes_moved == 1
    assert sum(populations[node] for node in graph if repaired.assignment[node] != source[node]) == 10
    validate_repaired_assignment(graph, repaired.assignment, "population", 25, 0.2)


def test_milp_shell_limit_is_not_reported_as_infeasibility() -> None:
    networkx_graph = nx.path_graph(5)
    nx.set_node_attributes(networkx_graph, {0: 10, 1: 10, 2: 10, 3: 10, 4: 10}, "population")
    graph = Graph.from_networkx(networkx_graph)
    with pytest.raises(AssignmentRepairSearchExhausted, match="max_shell_nodes"):
        repair_assignment_milp(
            graph,
            {0: "A", 1: "A", 2: "B", 3: "B", 4: "A"},
            "population",
            25,
            0.2,
            max_shell_nodes=1,
        )
