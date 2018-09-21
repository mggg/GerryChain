from rundmcmc.partition import Partition
from rundmcmc.updaters import (boundary_nodes, cut_edges, exterior_boundaries,
                               interior_boundaries, perimeter, polsby_popper,
                               Tally, cut_edges_by_part)


class GeographicPartition(Partition):
    default_updaters = {
        'perimeter': perimeter,
        'exterior_boundaries': exterior_boundaries,
        'interior_boundaries': interior_boundaries,
        'boundary_nodes': boundary_nodes,
        'cut_edges': cut_edges,
        'area': Tally('area', alias='area'),
        'polsby_popper': polsby_popper,
        'cut_edges_by_part': cut_edges_by_part
    }
