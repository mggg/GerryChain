import geopandas as gp
import networkx.readwrite
import json

from rundmcmc.chain import MarkovChain
from rundmcmc.make_graph import get_assignment_dict
from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.updaters import statistic_factory, cut_edges
from rundmcmc.metrics import mean_median
from rundmcmc.validity import Validator, contiguous


def main():
    # Sketch:
    #   1. Load dataframe.
    #   2. Construct neighbor information.
    #   3. Make a graph from this.
    #   4. Throw attributes into graph.
    df = gp.read_file("./testData/mo_cleaned_vtds.shp")

    with open("./testData/MO_graph.json") as f:
        graph_json = json.load(f)

    graph = networkx.readwrite.json_graph.adjacency_graph(graph_json)
    assignment = get_assignment_dict(df, "GEOID10", "CD")

    updaters = {'area': statistic_factory('ALAND10', alias='area'), 'cut_edges': cut_edges}
    initial_partition = Partition(graph, assignment, updaters)

    validator = Validator([contiguous])
    accept = lambda x: True

    chain = MarkovChain(propose_random_flip, validator, accept,
                        initial_partition, total_steps=100)

    for state in chain:
        print(mean_median(state, data_column='area'))

    print(graph.nodes(data=True))


if __name__ == "__main__":
    main()
