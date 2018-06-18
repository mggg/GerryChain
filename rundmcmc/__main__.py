from rundmcmc.ingest import ingest
from rundmcmc.make_graph import (add_data_to_graph, construct_graph,
                                 get_list_of_data, pull_districts)
from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.chain import MarkovChain
from rundmcmc.Runner import Runner
from rundmcmc.updaters import statistic_factory, cut_edges
from rundmcmc.validity import Validator, contiguous


def main():
    graph = construct_graph(*ingest("./testData/wyoming_test.shp", "GEOID"))

    cd_data = get_list_of_data('./testData/wyoming_test.shp', ['CD', 'ALAND'])

    add_data_to_graph(cd_data, graph, ['CD', 'ALAND'])

    assignment = pull_districts(graph, 'CD')
    validator = Validator([contiguous])
    updaters = {'area': statistic_factory('ALAND', alias='area'), 'cut_edges': cut_edges}

    initial_partition = Partition(graph, assignment, updaters)
    accept = lambda x: True
    # Exposes the chain object to the Runner.
    return MarkovChain(propose_random_flip, validator, accept, initial_partition, total_steps=10)


if __name__ == "__main__":
    # Wrap main()'s chain object in the Runner.
    Runner(main())
