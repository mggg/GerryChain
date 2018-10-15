from gerrychain.graph import Graph
from gerrychain.partition import Partition
from gerrychain.updaters import (
    Tally,
    boundary_nodes,
    cut_edges,
    cut_edges_by_part,
    exterior_boundaries,
    interior_boundaries,
    perimeter,
)


class GeographicPartition(Partition):
    """A :class:`Partition` with areas, perimeters, and boundary information included.
    These additional data allow you to compute compactness scores like
    `Polsby-Popper_ <https://en.wikipedia.org/wiki/Polsby-Popper_Test>`.
    """

    default_updaters = {
        "perimeter": perimeter,
        "exterior_boundaries": exterior_boundaries,
        "interior_boundaries": interior_boundaries,
        "boundary_nodes": boundary_nodes,
        "cut_edges": cut_edges,
        "area": Tally("area", alias="area"),
        "cut_edges_by_part": cut_edges_by_part,
    }

    @classmethod
    def from_file(cls, filename, assignment, updaters, columns=None):
        """Create a :class:`GeographicPartition` from an ESRI Shapefile, a GeoPackage,
        a GeoJSON file, or any other file that the `fiona` library can handle.
        """
        graph = Graph.from_file(filename, columns)
        cls(graph, assignment, updaters)
