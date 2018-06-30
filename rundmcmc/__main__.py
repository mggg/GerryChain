import functools

import matplotlib.pyplot as plt

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

    """
    updaters = {
        **votes_updaters(['PR_DV08', 'PR_RV08'], election_name='08'),
        'population': Tally('POP100', alias='population'),
        'cut_edges': cut_edges
    }
    return Partition(graph, assignment, updaters)
    """


def print_summary(partition, scores):
    bins = []
    print("")
    for name, score in scores.items():
        print(f"{name}: {score(partition, 'PR_DV08%')}")
        bins += [{name: score(partition, 'PR_DV08%')}]

    return bins


def main():
    initial_partition = PA_partition()

    chain = BasicChain(initial_partition, total_steps=10000)

    scores = {
        'Mean-Median': functools.partial(mean_median, proportion_column_name='VoteA%'),
        'Mean-Thirdian': functools.partial(mean_thirdian, proportion_column_name='VoteA%'),
        'Efficiency Gap': functools.partial(efficiency_gap, col1='VoteA', col2='VoteB'),
        'L1 Reciprocal Polsby-Popper': L1_reciprocal_polsby_popper
    }

    initial_scores = {key: score(initial_partition) for key, score in scores.items()}

    table = pipe_to_table(chain, scores)

    fig, axes = plt.subplots(2, 2)

    quadrants = {
        'Mean-Median': (0, 0),
        'Mean-Thirdian': (0, 1),
        'Efficiency Gap': (1, 0),
        'L1 Reciprocal Polsby-Popper': (1, 1)
    }

    for key in scores:
        quadrant = quadrants[key]
        axes[quadrant].hist(table[key], bins=50)
        axes[quadrant].set_title(key)
        axes[quadrant].axvline(x=initial_scores[key], color='r')
    plt.show()


if __name__ == "__main__":
    main()
