from rundmcmc.validity import (Validator, no_vanishing_districts,
                               Wsingle_flip_contiguous)
from rundmcmc.updaters import cut_edges, MetagraphDegree
from rundmcmc.proposals import propose_random_flip
from rundmcmc.make_graph import construct_graph
from rundmcmc.accept import always_accept
from rundmcmc.partition import Partition
from rundmcmc.chain import MarkovChain

# Some file that contains a graph with congressional district data.
path = "./35_rook.json"
steps = 1000

graph = construct_graph(path)
# Gross!
assignment = dict(zip(graph.nodes(), [graph.node[x]['CD'] for x in graph.nodes()]))

validator = Validator([no_vanishing_districts, single_flip_contiguous])

updaters = {'cut_edges': cut_edges,
            'metagraph_degree': MetagraphDegree(validator, "metagraph_degree")}

initial_partition = Partition(graph, assignment, updaters)

chain = MarkovChain(propose_random_flip, validator, always_accept,
                    initial_partition, total_steps=steps)

for i, partition in enumerate(chain):
    print("{}/{}".format(i + 1, steps))
    print(partition["metagraph_degree"])
