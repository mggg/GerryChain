from rundmcmc.ingest import ingest
from rundmcmc.make_graph import construct_graph, get_list_of_data, add_data_to_graph, pull_districts
from rundmcmc.validity import contiguous, Validator
from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.chain import MarkovChain
import matplotlib.pyplot as plt
import networkx as nx


def main():
    G = construct_graph(*ingest("./testData/wyoming_test.shp", "GEOID"))

    cd_data = get_list_of_data('./testData/wyoming_test.shp', ['CD', 'ALAND'])

    add_data_to_graph(cd_data, G, ['CD', 'ALAND'])

    assignment = pull_districts(G, 'CD')
    validator = Validator([contiguous])

    initial_partition = Partition(G, assignment, aggregate_fields=['ALAND'])
    accept = lambda x: True

    chain = MarkovChain(propose_random_flip, validator, accept, initial_partition, total_steps=10)

    for step in chain:
        print(step.assignment)


if __name__ == "__main__":
    main()
