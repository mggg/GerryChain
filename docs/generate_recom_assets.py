"""Regenerate the seeded images used by ``docs/user/recom.rst``."""

from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
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
DISTRICTR_COLORS = [
    "#0099cd",
    "#ffca5d",
    "#00cd99",
    "#99cd00",
    "#cd0099",
    "#9900cd",
    "#8dd3c7",
    "#bebada",
]


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


def assignment_image(graph, assignment):
    grid_size = int(len(assignment) ** 0.5)
    grid = np.empty((grid_size, grid_size))
    for node, district in assignment.items():
        grid[graph.node_data(node)["y"], graph.node_data(node)["x"]] = district

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(grid, cmap=ListedColormap(DISTRICTR_COLORS), vmin=0.5, vmax=8.5)
    ax.set_xticks(np.arange(-0.5, grid_size, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid_size, 1), minor=True)
    ax.grid(which="minor", color="black", linewidth=1)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(which="both", bottom=False, left=False)

    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    with Image.open(buffer) as image:
        return image.copy()


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
    save_ensemble(graph, assignments, "gerrymandria_ensemble.gif")

    graph, assignments = run_gerrymandria({"muni": 0.5}, 40, 2025)
    save_ensemble(graph, assignments, "gerrymandria_region_ensemble.gif")

    graph, assignments = run_gerrymandria({"muni": 0.2, "water_dist": 0.8}, 200, 2026)
    save_ensemble(
        graph,
        assignments[-40:],
        "gerrymandria_water_muni_ensemble.gif",
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
