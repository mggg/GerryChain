from rundmcmc.Graph import Graph

from rundmcmc.partition import Partition
from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               perimeters)
from rundmcmc.updaters import polsby_popper_updater as polsby_popper
from rundmcmc.updaters import votes_updaters
from rundmcmc.defaults import BasicChain
from rundmcmc.make_graph import construct_graph
from time import time
from rundmcmc.run import pipe_to_table
from rundmcmc.validity import (L1_reciprocal_polsby_popper, UpperBound,
                               Validator, no_vanishing_districts,
                               refuse_new_splits, contiguous, fast_connected,
                               proposed_changes_still_contiguous,
                               within_percent_of_ideal_population)

from rundmcmc.proposals import \
    propose_random_flip_no_loops as propose_random_flip
from rundmcmc.accept import always_accept
from rundmcmc.chain import MarkovChain

default_constraints = [#fast_connected,
                       proposed_changes_still_contiguous,
                       #contiguous,
                       no_vanishing_districts,
                       refuse_new_splits]


def main():
    G = Graph('./testData/MO_graph.json', geoid_col='id')
    G.add_data('testData/mo_cleaned_vtds.shp', id_col='GEOID10', col_names=['CD', 'POP100', 'ALAND10', 'USH_DV08', 'GEOID10'])
    G.id = 'GEOID10'
    assignment = dict(zip(G.nodes(), G.node_properties('CD')))
    updaters = {
        **votes_updaters(['USH_DV08', 'POP100']),
        'population': Tally('POP100', alias='population'),
        'perimeters': perimeters,
        'exterior_boundaries': exterior_boundaries,
        'boundary_nodes': boundary_nodes,
        'cut_edges': cut_edges,
        'areas': Tally('ALAND10', alias='areas'),
        'polsby_popper': polsby_popper,
        'cut_edges_by_part': cut_edges_by_part
    }

    G.convert()
    p = Partition(G, assignment, updaters)

    validator = Validator(default_constraints)

    chain = MarkovChain(propose_random_flip, validator, always_accept, initial_state=p, total_steps=30)

    print("MADE THE CHAIN")
    print(":) ")
    print(":-0")
    print(":-|")
    print(":-<")

    for step in chain:
        print(chain.counter)
    print("All done using ", default_constraints[0])

if __name__ == "__main__":
    import sys
    sys.path.append('/usr/local/Cellar/graph-tool/2.26_2/lib/python3.6/site-packages/')
    main()
