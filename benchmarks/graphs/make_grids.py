#!/usr/bin/env python3
"""Generate square grid dual graphs for benchmarking.

Writes grid_<n>x<n>.json files (in this directory) that benchmark_recom.py
can target via --json. Every node gets a population of 1 in "TOTPOP", e.g.:

    python benchmarks/benchmark_recom.py compare local git:main \
        --json benchmarks/grid_25x25.json --pop-col TOTPOP --parts 5
"""

from pathlib import Path

import networkx as nx

from gerrychain import Graph

HERE = Path(__file__).resolve().parent
SIZES = [8, 25, 50]


def make_grid(n: int) -> Graph:
    nx_graph = nx.grid_2d_graph(n, n)
    nx_graph = nx.convert_node_labels_to_integers(nx_graph, ordering="sorted")
    for node in nx_graph.nodes:
        nx_graph.nodes[node]["TOTPOP"] = 1
    return Graph.from_networkx(nx_graph)


def main() -> None:
    for n in SIZES:
        out = HERE / f"grid_{n}x{n}.json"
        graph = make_grid(n)
        graph.to_json(str(out))
        print(f"wrote {out} ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")


if __name__ == "__main__":
    main()
