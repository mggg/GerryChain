import geopandas as gp
import matplotlib.pyplot as plt

from rundmcmc.chain import MarkovChain
from rundmcmc.loggers import ConsoleLogger, FlatListLogger
from rundmcmc.make_graph import (add_data_to_graph, construct_graph,
                                 get_assignment_dict)
from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.run import run
from rundmcmc.updaters import cut_edges, statistic_factory
from rundmcmc.validity import Validator, contiguous


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
    updaters = {'area': statistic_factory('ALAND', alias='area'), 'cut_edges': cut_edges}
    initial_partition = Partition(graph, assignment, updaters)

    validator = Validator([contiguous])
    accept = lambda x: True

    chain = MarkovChain(propose_random_flip, validator, accept,
                        initial_partition, total_steps=100)

    loggers = [FlatListLogger('area'), ConsoleLogger(interval=10)]

    areas, success = run(chain, loggers)

    plt.hist(areas)
    plt.show()


if __name__ == "__main__":
    main()
