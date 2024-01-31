from typing import List, Any, Tuple
from ..graph import Graph


class SubgraphView:
    """
    A view for accessing subgraphs of :class:`Graph` objects.

    This class makes use of a subgraph cache to avoid recomputing subgraphs
    which can speed up computations when working with district assignments
    within a partition class.

    :ivar graph: The parent graph from which subgraphs are derived.
    :type graph: Graph
    :ivar parts: A list-of-lists dictionary (so a dict with key values indicated by
        the list index) mapping keys to subsets of nodes in the graph.
    :type parts: List[List[Any]]
    :ivar subgraphs_cache: Cache to store subgraph views for quick access.
    :type subgraphs_cache: Dict
    """

    __slots__ = ["graph", "parts", "subgraphs_cache"]

    def __init__(self, graph: Graph, parts: List[List[Any]]) -> None:
        """
        :param graph: The parent graph from which subgraphs are derived.
        :type graph: Graph
        :param parts: A list of lists of nodes corresponding the different
            parts of the partition of the graph.
        :type parts: List[List[Any]]

        :returns: None
        """
        self.graph = graph
        self.parts = parts
        self.subgraphs_cache = {}

    def __getitem__(self, part: int) -> Graph:
        """
        :param part: The the id of the partition to return the subgraph for.
        :type part: int

        :returns: The subgraph of the parent graph corresponding to the
            partition with id `part`.
        :rtype: Graph
        """
        if part not in self.subgraphs_cache:
            self.subgraphs_cache[part] = self.graph.subgraph(self.parts[part])
        return self.subgraphs_cache[part]

    def __iter__(self) -> Graph:
        for part in self.parts:
            yield self[part]

    def items(self) -> Tuple[int, Graph]:
        for part in self.parts:
            yield part, self[part]

    def __repr__(self) -> str:
        return (
            f"<SubgraphView with {len(self.parts)}"
            f" and {len(self.subgraphs_cache)} cached graphs>"
        )
