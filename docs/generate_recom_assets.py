"""Regenerate the seeded images used by ``docs/user/recom.rst``."""

from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from PIL import Image

from gerrychain import Election, GeographicPartition, Graph, MarkovChain, Partition
from gerrychain.accept import always_accept
from gerrychain.constraints import UpperBound, contiguous, within_percent_of_ideal_population
from gerrychain.proposals import build_recom_proposal_fn
from gerrychain.updaters import Tally, cut_edges

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
    "#ffffb3",
    "#a6cee3",
    "#1f78b4",
    "#b2df8a",
    "#33a02c",
    "#fb9a99",
    "#e31a1c",
    "#fdbf6f",
    "#ff7f00",
    "#cab2d6",
    "#6a3d9a",
    "#b15928",
    "#64ffda",
    "#00b8d4",
    "#a1887f",
    "#76ff03",
    "#dce775",
    "#b388ff",
    "#ff80ab",
    "#d81b60",
    "#26a69a",
    "#ffea00",
    "#6200ea",
)
LABEL_STYLE = {
    "color": "white",
    "fontsize": 16,
    "fontweight": "bold",
    "path_effects": [path_effects.withStroke(linewidth=2.5, foreground="black")],
}


def gerrymandria_setup():
    graph = Graph.from_json(STATIC / "gerrymandria.json")
    partition = Partition(
        graph,
        assignment="district",
        updaters={"population": Tally("TOTPOP"), "cut_edges": cut_edges},
    )
    ideal_population = sum(partition["population"].values()) / len(partition)
    return partition, ideal_population


def run_gerrymandria(region_surcharge, steps, seed):
    partition, ideal_population = gerrymandria_setup()
    proposal = build_recom_proposal_fn(
        pop_col="TOTPOP",
        pop_target=ideal_population,
        epsilon=0.01,
        region_surcharge=region_surcharge,
    )
    chain = MarkovChain(
        proposal=proposal,
        constraints=[contiguous],
        accept=always_accept,
        initial_state=partition,
        total_steps=steps,
        rng=seed,
    )
    return partition.graph, [state.assignment for state in chain]


def assignment_image(graph, assignment, show_labels=False):
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


def save_district_dual_graph(graph):
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


def save_ensemble(graph, assignments, gif_name, png_name=None):
    frames = [assignment_image(graph, assignment) for assignment in assignments]
    frames[0].save(
        IMAGES / gif_name,
        save_all=True,
        append_images=frames[1:],
        duration=500,
        loop=0,
    )
    if png_name is not None:
        frames[-1].save(IMAGES / png_name)


def regenerate_gerrymandria():
    graph, assignments = run_gerrymandria(None, 40, 2024)
    for filename, attribute in (
        ("gerrymandria.png", "district"),
        ("gerrymandria_cities.png", "muni"),
        ("gerrymandria_county.png", "county"),
        ("gerrymandria_water.png", "water_dist"),
    ):
        assignment = {node: graph.node_data(node)[attribute] for node in graph.nodes}
        assignment_image(graph, assignment, show_labels=True).save(IMAGES / filename)
    save_district_dual_graph(graph)

    save_ensemble(graph, assignments, "gerrymandria_grid_ensemble.gif")

    graph, assignments = run_gerrymandria({"muni": 0.5}, 40, 2025)
    save_ensemble(graph, assignments, "gerrymandria_region_grid_ensemble.gif")

    graph, assignments = run_gerrymandria({"muni": 0.2, "water_dist": 0.8}, 200, 2026)
    save_ensemble(
        graph,
        assignments[-40:],
        "gerrymandria_water_muni_grid_ensemble.gif",
        "gerrymandria_water_and_muni_aware.png",
    )


def regenerate_pa_plot():
    graph = Graph.from_json(STATIC / "PA_VTDs.json")
    elections = [
        Election("SEN10", {"Democratic": "SEN10D", "Republican": "SEN10R"}),
        Election("SEN12", {"Democratic": "USS12D", "Republican": "USS12R"}),
        Election("SEN16", {"Democratic": "T16SEND", "Republican": "T16SENR"}),
        Election("PRES12", {"Democratic": "PRES12D", "Republican": "PRES12R"}),
        Election("PRES16", {"Democratic": "T16PRESD", "Republican": "T16PRESR"}),
    ]
    updaters = {"population": Tally("TOT_POP", alias="population")}
    updaters.update({election.name: election for election in elections})
    partition = GeographicPartition(graph, assignment="2011_PLA_1", updaters=updaters)
    ideal_population = sum(partition["population"].values()) / len(partition)
    proposal = build_recom_proposal_fn(
        pop_col="TOT_POP",
        pop_target=ideal_population,
        epsilon=0.02,
    )
    compactness_bound = UpperBound(
        lambda part: len(part["cut_edges"]), 2 * len(partition["cut_edges"])
    )
    chain = MarkovChain(
        proposal=proposal,
        constraints=[within_percent_of_ideal_population(partition, 0.02), compactness_bound],
        accept=always_accept,
        initial_state=partition,
        total_steps=1000,
        rng=2024,
    )
    data = pd.DataFrame(sorted(state["SEN12"].percents("Democratic")) for state in chain)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.axhline(0.5, color="#cccccc")
    data.boxplot(ax=ax, positions=range(len(data.columns)))
    ax.plot(data.iloc[0], "ro")
    ax.set_title("Comparing the 2011 plan to an ensemble")
    ax.set_ylabel("Democratic vote % (Senate 2012)")
    ax.set_xlabel("Sorted districts")
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
    fig.savefig(IMAGES / "recom_plot.svg")
    plt.close(fig)


if __name__ == "__main__":
    regenerate_gerrymandria()
    regenerate_pa_plot()
