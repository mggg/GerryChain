import geopandas as gp

from rundmcmc.chain import MarkovChain
from rundmcmc.make_graph import (add_data_to_graph, construct_graph,
                                 get_assignment_dict)
from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.updaters import statistic_factory
from rundmcmc.validity import Validator, contiguous
from rundmcmc.metrics import mean_median


def main():
    # Sketch:
    #   1. Load dataframe.
    #   2. Construct neighbor information.
    #   3. Make a graph from this.
    #   4. Throw attributes into graph.
    df = gp.read_file("./testData/wyoming_test.shp")
    graph = construct_graph(df, geoid_col="GEOID")
    add_data_to_graph(df, graph, ['CD', 'ALAND'], id_col='GEOID')

    assignment = get_assignment_dict(df, "GEOID", "CD")
    updaters = {'area': statistic_factory('ALAND', alias='area')}
    initial_partition = Partition(graph, assignment, updaters)

    validator = Validator([contiguous])
    accept = lambda x: True

    chain = MarkovChain(propose_random_flip, validator, accept,
                        initial_partition, total_steps=100)

    for state in chain:
        print(mean_median(state, data_column='area'))


if __name__ == "__main__":
    main()
