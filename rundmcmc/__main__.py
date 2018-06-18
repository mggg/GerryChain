from rundmcmc.make_graph import construct_graph, add_data_to_graph, get_assignment_dict
from rundmcmc.validity import contiguous, Validator
from rundmcmc.partition import Partition, propose_random_flip
from rundmcmc.chain import MarkovChain
from rundmcmc.updaters import statistic_factory
import geopandas as gp


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

    validator = Validator([contiguous])
    updaters = {'area': statistic_factory('ALAND', alias='area')}

    initial_partition = Partition(graph, assignment, updaters)
    accept = lambda x: True

    chain = MarkovChain(propose_random_flip, validator, accept, initial_partition, total_steps=10)

    for step in chain:
        print(step.assignment)


if __name__ == "__main__":
    main()
