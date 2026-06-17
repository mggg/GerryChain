"""Small, self-contained example graphs that ship with GerryChain.

These exist so that documentation examples, quick experiments, and tests can use a real graph
without depending on an external data file or a particular working directory. The data is shipped
inside the installed package and loaded via :mod:`importlib.resources`.
"""

from importlib.resources import as_file, files

from ..graph import Graph

__all__ = ["gerrymandria"]


def gerrymandria() -> Graph:
    """Return the "Gerrymandria" toy graph used throughout the GerryChain documentation.

    Gerrymandria is a fictional 8x8 grid "state" of 64 unit-population nodes. It is the canonical
    example for *region-aware* recombination, because every node carries several region labels, so
    you can demonstrate biasing a spanning tree (and the resulting districts) to keep a region
    whole. Each node has the following attributes:

    * ``"county"`` - one of 4 counties (a 4x4 block of nodes each),
    * ``"muni"`` - one of 16 municipalities (a 2x2 block of nodes each),
    * ``"water_dist"`` - one of 4 water districts,
    * ``"district"`` - a seed districting plan with 8 districts of 8 nodes each,
    * ``"TOTPOP"`` - total population (1 for every node),
    * ``"x"`` / ``"y"`` - grid coordinates in ``range(8)``,
    * plus ``"precinct"``, ``"boundary_node"`` and ``"boundary_perim"``.

    The graph is loaded from JSON shipped inside the package, so it works from anywhere without an
    external file.

    Returns:
        Graph: the Gerrymandria example graph (a NetworkX-backed GerryChain ``Graph``).

    Example:
        >>> from gerrychain.examples import gerrymandria
        >>> graph = gerrymandria()
        >>> len(graph.nodes)
        64
        >>> sorted({graph.node_data(n)["county"] for n in graph.node_indices})
        ['1', '2', '3', '4']
    """
    resource = files(__package__).joinpath("gerrymandria.json")
    with as_file(resource) as path:
        return Graph.from_json(str(path))
