import json

import networkx

from rundmcmc.partition import Partition
from rundmcmc.updaters import (boundary_nodes, cut_edges, exterior_boundaries,
                               interior_boundaries, perimeters, polsby_popper,
                               Tally, cut_edges_by_part)


class GeographicPartition(Partition):
    default_updaters = {
        'perimeters': perimeters,
        'exterior_boundaries': exterior_boundaries,
        'interior_boundaries': interior_boundaries,
        'boundary_nodes': boundary_nodes,
        'cut_edges': cut_edges,
        'areas': Tally('area', alias='areas'),
        'polsby_popper': polsby_popper,
        'cut_edges_by_part': cut_edges_by_part
    }

    @classmethod
    def from_json_graph(cls, graph_path, assignment):
        with open(graph_path) as f:
            graph_data = json.load(f)
        graph = networkx.readwrite.adjacency_graph(graph_data)

        if isinstance(assignment, str):
            assignment = {node: graph.nodes[node][assignment]
                          for node in graph.nodes}
        elif not isinstance(assignment, dict):
            raise TypeError("Assignment must be a dict or a node attribute key")

        updaters = cls.default_updaters
        return cls(graph, assignment, updaters)
