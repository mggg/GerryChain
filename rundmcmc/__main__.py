import json

import geopandas as gp
import networkx.readwrite
import psutil as ps
import matplotlib.pyplot as plt
import sys
import os

from rundmcmc.defaults import BasicChain
from rundmcmc.make_graph import add_data_to_graph, get_assignment_dict
from rundmcmc.partition import Partition
from rundmcmc.scores import mean_median, mean_thirdian
from rundmcmc.updaters import Tally, cut_edges, votes_updaters


def example_partition():
    df = gp.read_file("./testData/mo_cleaned_vtds.shp")

    with open("./testData/MO_graph.json") as f:
        graph_json = json.load(f)

    graph = networkx.readwrite.json_graph.adjacency_graph(graph_json)

    assignment = get_assignment_dict(df, "GEOID10", "CD")

    add_data_to_graph(df, graph, ['PR_DV08', 'PR_RV08', 'POP100'], id_col='GEOID10')

    updaters = {
        **votes_updaters(['PR_DV08', 'PR_RV08'], election_name='08'),
        'population': Tally('POP100', alias='population'),
        'cut_edges': cut_edges
    }
    return Partition(graph, assignment, updaters)


def print_summary(partition, scores):
    bins = []
    print("")
    for name, score in scores.items():
        print(f"{name}: {score(partition, 'PR_DV08%')}")
        bins += [{name: score(partition, 'PR_DV08%')}]

    return bins


def main():
    initial_partition = example_partition()

    chain = BasicChain(initial_partition, total_steps=100)

    scores = {
        'Mean-Median': mean_median,
        'Mean-Thirdian': mean_thirdian
    }

    process = ps.Process(os.getpid())
    start = process.memory_info().rss
    total = ps.virtual_memory()[0]

    hist = []
    mem_usage = []
    num_inside = []

    for partition in chain:
        data = print_summary(partition, scores)
        hist += data

        """
            Try and mock a histogram by tracking all the data from start to
            finish on a billion iterations of the chain.
        """
        available = process.memory_info().rss
        used = available
        mem_usage += [100 * ((used - start) / total)]
        num_inside += [len(mem_usage)]

    iterations = list(range(0, len(mem_usage)))

    """
        Generate histograms of how the number of things in the histogram scale
        compared to how much memory is actually being used.
    """
    plt.scatter(iterations, mem_usage, c="r", label="% memory used")
    plt.show()


if __name__ == "__main__":
    main()
