import geopandas as gp
import networkx.readwrite

from rundmcmc.chain import MarkovChain
from rundmcmc.make_graph import add_data_to_graph, get_assignment_dict
from rundmcmc.partition import Partition
from rundmcmc.proposals import propose_random_flip
from rundmcmc.scores import efficiency_gap, mean_median, mean_thirdian
from rundmcmc.updaters import cut_edges, votes_updaters
from rundmcmc.validity import Validator, contiguous


def example_partition():
    df = gp.read_file("./testData/mo_cleaned_vtds.shp")
    graph = networkx.readwrite.read_gpickle('example_graph.gpickle')
    assignment = get_assignment_dict(df, "GEOID10", "CD")

    add_data_to_graph(df, graph, ['PR_DV08', 'PR_RV08'], id_col='GEOID10')

    updaters = {
        **votes_updaters(['PR_DV08', 'PR_RV08'], election_name='08'),
        'cut_edges': cut_edges
    }
    return Partition(graph, assignment, updaters)


def always_accept(partition):
    return True


def print_summary(partition, scores):
    print("")
    for name, score in scores.items():
        print(f"{name}: {score(partition, 'PR_DV08%')}")


def main():
    # Sketch:
    #   1. Load dataframe.
    #   2. Construct neighbor information.
    #   3. Make a graph from this.
    #   4. Throw attributes into graph.
    initial_partition = example_partition()

    chain = MarkovChain(propose_random_flip, Validator([contiguous]), always_accept,
                        initial_partition, total_steps=100)

    scores = {
        'Efficiency Gap': efficiency_gap,
        'Mean-Median': mean_median,
        'Mean-Thirdian': mean_thirdian
    }

    for partition in chain:
        print_summary(partition, scores)


if __name__ == "__main__":
    main()
