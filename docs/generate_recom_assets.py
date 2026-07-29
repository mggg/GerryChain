"""Regenerate the static Gerrymandria plan and region assets used by the docs."""

import random
from io import BytesIO
from pathlib import Path
from collections.abc import Hashable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from PIL import Image

from gerrychain import Graph, MarkovChain, Partition, accept, updaters
from gerrychain.constraints import contiguous
from gerrychain.examples import gerrymandria
from gerrychain.proposals import ReCom

Point = tuple[int, int]
Segment = tuple[Point, Point]

DOCS = Path(__file__).parent
IMAGES = DOCS / "user" / "images"
DISTRICTR_COLORS = (
    "#0099cd",
    "#ffca5d",
    "#00cd99",
    "#99cd00",
    "#cd0099",
    "#9900cd",
    "#8dd3c7",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#bc80bd",
    "#ccebc5",
    "#ffed6f",
)
LABEL_STYLE = {
    "color": "white",
    "fontsize": 16,
    "fontweight": "bold",
    "path_effects": [path_effects.withStroke(linewidth=2.5, foreground="black")],
}


def assignment_image(
    graph: Graph,
    assignment: Mapping[Hashable, Hashable],
    show_labels: bool = False,
    tree_edges: Sequence[Segment] | None = None,
    cut_edge: Segment | None = None,
) -> Image.Image:
    """Render a plan as a colored grid, optionally overlaying a spanning tree and its cut edge.

    ``tree_edges`` and ``cut_edge`` are given in grid coordinates rather than node ids, because the
    spanning tree is built on a subgraph whose node ids are renumbered from the parent graph's.
    """
    grid_size = int(len(assignment) ** 0.5)
    grid = np.empty((grid_size, grid_size))
    labels = sorted(set(assignment.values()), key=int)
    color_index = {label: index for index, label in enumerate(labels)}
    for node, label in assignment.items():
        grid[graph.node_data(node)["y"], graph.node_data(node)["x"]] = color_index[label]

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(
        grid,
        cmap=ListedColormap(DISTRICTR_COLORS[: len(labels)]),
        vmin=-0.5,
        vmax=len(labels) - 0.5,
    )
    ax.set_xticks(np.arange(-0.5, grid_size, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid_size, 1), minor=True)
    ax.grid(which="minor", color="black", linewidth=1)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(which="both", bottom=False, left=False)
    if show_labels:
        for node, label in assignment.items():
            data = graph.node_data(node)
            ax.text(
                data["x"],
                data["y"],
                str(label),
                ha="center",
                va="center",
                **LABEL_STYLE,
            )

    if tree_edges:
        for (x1, y1), (x2, y2) in tree_edges:
            ax.plot([x1, x2], [y1, y2], color="black", linewidth=2, zorder=2)
    if cut_edge is not None:
        # Drawn above the tree edges but below the nodes, so the cut reads as a severed
        # connection between two nodes rather than a line laid over them.
        (x1, y1), (x2, y2) = cut_edge
        ax.plot([x1, x2], [y1, y2], color="white", linewidth=5, zorder=3)
    if tree_edges:
        ax.scatter(
            [x for edge in tree_edges for x, _ in edge],
            [y for edge in tree_edges for _, y in edge],
            s=250,
            c="#e6e6e6",
            edgecolors="black",
            linewidths=1,
            zorder=4,
        )

    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buffer.seek(0)
    with Image.open(buffer) as image:
        return image.copy()


def save_district_dual_graph(graph: Graph) -> None:
    assignment = {node: graph.node_data(node)["district"] for node in graph.nodes}
    labels = sorted(set(assignment.values()), key=int)
    color_index = {label: index for index, label in enumerate(labels)}
    positions = {
        node: (graph.node_data(node)["x"], -graph.node_data(node)["y"]) for node in graph.nodes
    }

    fig, ax = plt.subplots(figsize=(8, 8))
    for node, neighbor in graph.edges:
        x_values = (positions[node][0], positions[neighbor][0])
        y_values = (positions[node][1], positions[neighbor][1])
        ax.plot(x_values, y_values, color="black", linewidth=1, zorder=1)
    ax.scatter(
        [positions[node][0] for node in graph.nodes],
        [positions[node][1] for node in graph.nodes],
        c=[DISTRICTR_COLORS[color_index[assignment[node]]] for node in graph.nodes],
        edgecolors="black",
        s=1200,
        zorder=2,
    )
    for node in graph.nodes:
        ax.text(
            *positions[node],
            assignment[node],
            ha="center",
            va="center",
            zorder=3,
            **LABEL_STYLE,
        )
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(IMAGES / "gerrymandria_district.png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)


DemoFrame = tuple[dict[Hashable, Hashable], list[Segment] | None, Segment | None]


def _edges_between(
    graph: Graph,
    sources: set[Hashable],
    targets: set[Hashable],
) -> list[tuple[Hashable, Hashable]]:
    """Every graph edge running from ``sources`` into ``targets``, in a stable order."""
    pairs = ((node, n) for node in sources for n in graph.neighbors(node) if n in targets)
    return sorted(pairs, key=str)


def _adjacent_district_pairs(
    graph: Graph,
    assignment: Mapping[Hashable, Hashable],
) -> list[tuple[Hashable, Hashable]]:
    """Every pair of districts that share a boundary, in a stable order."""
    pairs = {
        tuple(sorted((assignment[node], assignment[n]), key=str))
        for node in assignment
        for n in graph.neighbors(node)
        if assignment[node] != assignment[n]
    }
    return sorted(pairs, key=str)


def _spanning_tree_edges(
    graph: Graph,
    nodes: set[Hashable],
    rng: random.Random,
) -> list[tuple[Hashable, Hashable]]:
    """Draw a random spanning tree over an induced set of nodes, growing it one edge at a time."""
    seen = {min(nodes, key=str)}
    edges = []
    while seen != nodes:
        edge = rng.choice(_edges_between(graph, seen, nodes - seen))
        edges.append(edge)
        seen.add(edge[1])
    return edges


def recom_demo_frames(
    graph: Graph,
    *,
    seed: int,
    total_steps: int,
) -> list[DemoFrame]:
    """Build frames showing how ReCom turns one pair of districts into the next."""
    assignments = recom_assignments(graph, seed=seed, total_steps=total_steps)
    rng = random.Random(seed)

    def point(node_id: Hashable) -> Point:
        data = graph.node_data(node_id)
        return (data["x"], data["y"])

    frames: list[DemoFrame] = [(assignments[0], None, None)]
    for before, after in zip(assignments, assignments[1:]):
        moved = next((node for node in before if before[node] != after[node]), None)
        if moved is not None:
            # A node that moved went from one district of the merged pair to the other, so its old
            # and new labels name both of them.
            label_a, label_b = sorted({before[moved], after[moved]}, key=str)
        else:
            # ReCom re-split a merged pair exactly as it was, so the plan is unchanged and nothing
            # identifies which pair it merged. Any adjacent pair illustrates the step, because
            # cutting the bridge between two districts' trees always restores those districts.
            label_a, label_b = rng.choice(_adjacent_district_pairs(graph, after))
        part_a = {node for node in after if after[node] == label_a}
        part_b = {node for node in after if after[node] == label_b}
        bridge = rng.choice(_edges_between(graph, part_a, part_b))
        tree = [
            *_spanning_tree_edges(graph, part_a, rng),
            *_spanning_tree_edges(graph, part_b, rng),
            bridge,
        ]

        tree_edges = [(point(node1), point(node2)) for node1, node2 in tree]
        frames.append((before, tree_edges, None))
        frames.append((before, tree_edges, (point(bridge[0]), point(bridge[1]))))
        frames.append((after, None, None))
    return frames


def recom_assignments(
    graph: Graph,
    *,
    seed: int,
    total_steps: int,
    region_surcharge: dict[str, float] | None = None,
) -> list[dict[Hashable, Hashable]]:
    """Run the seeded Gerrymandria chain used to render a plan sequence."""
    chain = MarkovChain(total_steps=total_steps, rng=seed)
    chain.initial_partition = Partition(graph, assignment="district")
    chain.add_updaters(
        {
            "population": updaters.Tally("TOTPOP", alias="population"),
            "cut_edges": updaters.cut_edges,
        }
    )
    pop_target = sum(chain.initial_partition["population"].values()) / len(chain.initial_partition)
    chain.proposal_fn = ReCom.district_pairs_mst(
        pop_col="TOTPOP",
        pop_target=pop_target,
        epsilon=0.01,
        region_surcharge=region_surcharge,
    )
    chain.add_constraint(contiguous)
    chain.acceptance_fn = accept.always_accept
    return [dict(state.assignment.mapping) for state in chain]


def save_assignment_gif(
    graph: Graph,
    assignments: Sequence[Mapping[Hashable, Hashable]],
    filename: str,
) -> None:
    """Render a sequence of assignments as a looping GIF."""
    images = [assignment_image(graph, assignment) for assignment in assignments]
    images[0].save(
        IMAGES / filename,
        save_all=True,
        append_images=images[1:],
        duration=500,
        loop=0,
    )


def save_demo_gif(graph: Graph, frames: Sequence[DemoFrame], filename: str) -> None:
    """Render the tree-and-cut demo frames as a looping GIF."""
    images = [
        assignment_image(graph, assignment, tree_edges=tree_edges, cut_edge=cut_edge)
        for assignment, tree_edges, cut_edge in frames
    ]
    images[0].save(
        IMAGES / filename,
        save_all=True,
        append_images=images[1:],
        duration=500,
        loop=0,
    )


def regenerate_gerrymandria() -> None:
    graph = gerrymandria()
    for filename, attribute in (
        ("gerrymandria.png", "district"),
        ("gerrymandria_cities.png", "muni"),
        ("gerrymandria_water.png", "water_dist"),
        ("gerrymandria_county.png", "county"),
    ):
        assignment = {node: graph.node_data(node)[attribute] for node in graph.nodes}
        assignment_image(graph, assignment, show_labels=True).save(IMAGES / filename)
    save_district_dual_graph(graph)

    # The hero animation for the ReCom guide: unlike the plain ensemble gif below, this one shows
    # the spanning tree and the cut edge that produce each new pair of districts.
    save_demo_gif(
        graph,
        recom_demo_frames(graph, seed=42, total_steps=20),
        "gerrychain_demo.gif",
    )

    simple_assignments = recom_assignments(graph, seed=2024, total_steps=40)
    save_assignment_gif(graph, simple_assignments, "gerrymandria_grid_ensemble.gif")

    municipality_assignments = recom_assignments(
        graph,
        seed=2025,
        total_steps=40,
        region_surcharge={"muni": 0.5},
    )
    save_assignment_gif(
        graph,
        municipality_assignments,
        "gerrymandria_region_grid_ensemble.gif",
    )

    water_municipality_assignments = recom_assignments(
        graph,
        seed=42,
        total_steps=200,
        region_surcharge={"muni": 0.2, "water_dist": 0.8},
    )
    save_assignment_gif(
        graph,
        water_municipality_assignments[-40:],
        "gerrymandria_water_muni_grid_ensemble.gif",
    )
    assignment_image(graph, water_municipality_assignments[-1]).save(
        IMAGES / "gerrymandria_water_and_muni_aware.png"
    )


if __name__ == "__main__":
    regenerate_gerrymandria()
