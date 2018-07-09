from rundmcmc.Graph import Graph

from rundmcmc.partition import Partition
from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               perimeters)
from rundmcmc.updaters import polsby_popper_updater as polsby_popper
from rundmcmc.updaters import votes_updaters
from rundmcmc.defaults import BasicChain
from time import time
from rundmcmc.run import pipe_to_table

def main():
    G = Graph("./testData/PA_graph_with_data.json")
    assignment = dict(zip(G.nodes(), G.node_properties('CD')))
    updaters = {
        **votes_updaters(['VoteA', 'VoteB']),
        'population': Tally('POP100', alias='population'),
        'perimeters': perimeters,
        'exterior_boundaries': exterior_boundaries,
        'boundary_nodes': boundary_nodes,
        'cut_edges': cut_edges,
        'areas': Tally('ALAND10', alias='areas'),
        'polsby_popper': polsby_popper,
        'cut_edges_by_part': cut_edges_by_part
    }

    p = Partition(G, assignment, updaters)
    G.convert()

    chain = BasicChain(p, 30)

if __name__ == "__main__":
    import sys
    sys.path.append('/usr/local/Cellar/graph-tool/2.26_2/lib/python3.6/site-packages/')
    main()
