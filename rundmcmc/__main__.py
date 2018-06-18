import matplotlib.pyplot as plt

from rundmcmc.chain import MarkovChain
from rundmcmc.ingest import ingest
from rundmcmc.loggers import ConsoleLogger, FlatListLogger
from rundmcmc.make_graph import (add_data_to_graph, construct_graph,
                                 get_list_of_data, pull_districts)
from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.run import run
from rundmcmc.updaters import cut_edges, statistic_factory
from rundmcmc.validity import Validator, contiguous


def main():
    graph = construct_graph(*ingest('./testData/wyoming_test.shp', 'GEOID'))
    cd_data = get_list_of_data('./testData/wyoming_test.shp', ['CD', 'ALAND'])
    add_data_to_graph(cd_data, graph, ['CD', 'ALAND'])

    assignment = pull_districts(graph, 'CD')
    updaters = {
        'area': statistic_factory('ALAND', alias='area'),
        'cut_edges': cut_edges
    }
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
