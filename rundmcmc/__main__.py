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

    chain = BasicChain(p, 30)
    for step in chain:
        print(chain.counter)

if __name__ == "__main__":
    import sys
    sys.path.append('/usr/local/Cellar/graph-tool/2.26_2/lib/python3.6/site-packages/')
    main()
