from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph, get_list_of_data, add_data_to_graph, pull_districts
from rundmcmc.validity import contiguous, Validator
from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.chain import MarkovChain
from rundmcmc.updaters import statistic_factory
import time


def main():
    graph = construct_graph(*ingest("./testData/wyoming_test.shp", "GEOID"))

    cd_data = get_list_of_data('./testData/wyoming_test.shp', ['CD', 'ALAND'])

    add_data_to_graph(cd_data, graph, ['CD', 'ALAND'])

    assignment = pull_districts(graph, 'CD')
    validator = Validator([contiguous])
    updaters = {'area': statistic_factory('ALAND', alias='area')}

    initial_partition = Partition(graph, assignment, updaters)
    accept = lambda x: True

    n = 2**15
    chain = MarkovChain(propose_random_flip, validator, accept, initial_partition, total_steps=n)

    i = 0
    print("starting")
    start = time.time()
    for step in chain:
        # print(step.assignment)
        if i % 2**10 == 0:
            print(i)
        i += 1
    print(time.time() - start)


if __name__ == "__main__":
    import sys
    sys.path.append('/usr/local/Cellar/graph-tool/2.26_2/lib/python3.6/site-packages/')
    main()
