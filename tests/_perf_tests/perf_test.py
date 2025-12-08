# Code copied from the GerryChain User Guide / Tutorial:

import matplotlib.pyplot as plt
from gerrychain import (Partition, Graph, MarkovChain,
                        updaters, constraints, accept)
from gerrychain.proposals import recom
from gerrychain.constraints import contiguous
from functools import partial
import pandas

import cProfile

# Set the random seed so that the results are reproducible!
import random

def main():

    random.seed(2024)
    graph = Graph.from_json("./gerrymandria.json")
    
    my_updaters = {
        "population": updaters.Tally("TOTPOP"),
        "cut_edges": updaters.cut_edges
    }
    
    initial_partition = Partition(
        graph,
        assignment="district",
        updaters=my_updaters
    )
    
    # This should be 8 since each district has 1 person in it.
    # Note that the key "population" corresponds to the population updater
    # that we defined above and not with the population column in the json file.
    ideal_population = sum(initial_partition["population"].values()) / len(initial_partition)
    
    proposal = partial(
        recom,
        pop_col="TOTPOP",
        pop_target=ideal_population,
        epsilon=0.01,
        node_repeats=2
    )
    
    recom_chain = MarkovChain(
        proposal=proposal,
        constraints=[contiguous],
        accept=accept.always_accept,
        initial_state=initial_partition,
        total_steps=40
    )

    assignments = list(recom_chain)
    
    assignment_list = []
    
    for i, item in enumerate(recom_chain):
        print(f"Finished step {i+1}/{len(recom_chain)}", end="\r")
        assignment_list.append(item.assignment)
    
if __name__ == "__main__":
    cProfile.run('main()', sort='tottime')

