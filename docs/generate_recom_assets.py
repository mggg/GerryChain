"""Regenerate the Gerrymandria maps used by ``docs/user/recom.ipynb``.

The old RST docs also used seeded ensemble animations and a PA boxplot; the tutorial
notebooks now render their plots live, so only the static region/seed-plan maps remain.
"""

from io import BytesIO
from pathlib import Path
from collections.abc import Hashable, Mapping

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from PIL import Image

from gerrychain import Graph

DOCS = Path(__file__).parent
STATIC = DOCS / "_static"
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
) -> Image.Image:
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


def regenerate_gerrymandria() -> None:
    graph = Graph.from_json(STATIC / "gerrymandria.json")
    for filename, attribute in (
        ("gerrymandria.png", "district"),
        ("gerrymandria_cities.png", "muni"),
        ("gerrymandria_water.png", "water_dist"),
    ):
        assignment = {node: graph.node_data(node)[attribute] for node in graph.nodes}
        assignment_image(graph, assignment, show_labels=True).save(IMAGES / filename)
    save_district_dual_graph(graph)


if __name__ == "__main__":
    regenerate_gerrymandria()
