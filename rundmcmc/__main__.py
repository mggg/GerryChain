
from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph, get_list_of_data, add_data_to_graph, pull_districts
from rundmcmc.validity import contiguous, Validator, fast_connected
from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.chain import MarkovChain
from rundmcmc.Logger import Logger
from rundmcmc.updaters import statistic_factory
import time


def main():
    # Time the creation of the dual graph.
    start = time.time()
    print("Constructing dual graph.")
    graph = construct_graph(*ingest("./testData/wyoming_test.shp", "GEOID"))
    end = time.time()
    print("Done in {} seconds.\n".format(str(end - start)))

    print("Reading in area data and congressional district assignments.")
    cd_data = get_list_of_data('./testData/wyoming_test.shp', ['CD', 'ALAND'])
    print("Done.\n")

    print("Adding data to the graph.")
    add_data_to_graph(cd_data, graph, ['CD', 'ALAND'])
    print("Done.\n")

    print("Initializing a Partition, Validator, and updaters.")
    assignment = pull_districts(graph, 'CD')
    validator = Validator([fast_connected])
    updaters = {'area': statistic_factory('ALAND', alias='area')}

    initial_partition = Partition(graph, assignment, updaters)
    accept = lambda x: True
    print("Done. Moving on to the chain.\n")

    # Exposes the chain object to the Logger.
    return MarkovChain(propose_random_flip, validator, accept, initial_partition, total_steps=2**15)


if __name__ == "__main__":
    # Wrap main()'s chain object in the Logger.
    Logger(main(), console=False)
