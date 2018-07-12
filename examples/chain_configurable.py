from rundmcmc.validity import (Validator, no_vanishing_districts,
                               refuse_new_splits, single_flip_contiguous)
from rundmcmc.proposals import propose_random_flip
from rundmcmc.make_graph import construct_graph
from rundmcmc.accept import always_accept
from rundmcmc.partition import Partition
from rundmcmc.updaters import cut_edges
from rundmcmc.chain import MarkovChain

# Some file that contains a graph with congressional district data.
path = "./45_rook.json"
steps = 1000

graph = construct_graph(path)
# Gross!
assignment = dict(zip(graph.nodes(), [graph.node[x]['CD'] for x in graph.nodes()]))

updaters = {'cut_edges': cut_edges}

initial_partition = Partition(graph, assignment, updaters)

validator = Validator([refuse_new_splits, no_vanishing_districts, single_flip_contiguous])
chain = MarkovChain(propose_random_flip, validator, always_accept,
                    initial_partition, total_steps=steps)

for i, partition in enumerate(chain):
    print("{}/{}".format(i + 1, steps))
    print(partition.assignment)
