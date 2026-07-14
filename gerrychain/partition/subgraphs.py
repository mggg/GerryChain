from collections.abc import Hashable, Iterable, Iterator, Mapping

from ..graph import FrozenGraph, Graph


class SubgraphView:
    """
    A view for accessing subgraphs of Graph objects.

    This class makes use of a subgraph cache to avoid recomputing subgraphs
    which can speed up computations when working with district assignments
    within a partition class.

    Attributes:
        graph (Graph): The parent graph from which subgraphs are derived.
        parts (Mapping[Hashable, Iterable[Hashable]]): Parts mapped to their nodes.
        subgraphs_cache (dict[Hashable, Graph | FrozenGraph]): Cached subgraphs by part.
    """

    __slots__ = ["graph", "parts", "subgraphs_cache"]

    def __init__(
        self, graph: Graph | FrozenGraph, parts: Mapping[Hashable, Iterable[Hashable]]
    ) -> None:
        """Initialize a SubgraphView instance.

        Args:
            graph (Graph | FrozenGraph): The parent graph from which subgraphs are derived.
            parts (Mapping[Hashable, Iterable[Hashable]]): Parts mapped to their nodes.

        """
        self.graph = graph
        self.parts = parts
        self.subgraphs_cache: dict[Hashable, Graph | FrozenGraph] = {}

    def __getitem__(self, part: Hashable) -> Graph | FrozenGraph:
        """Return the item for the given key.

        This method returns the item for the given key. It returns subgraph of the parent graph
        corresponding to the partition with id `part`.

        Args:
            part (Hashable): The the id of the partition to return the subgraph for.

        Returns:
            Graph | FrozenGraph: The subgraph corresponding to the part ID.
        """
        if part not in self.subgraphs_cache:
            self.subgraphs_cache[part] = self.graph.subgraph(self.parts[part])
        return self.subgraphs_cache[part]

    def __iter__(self) -> Iterator[Graph | FrozenGraph]:
        for part in self.parts:
            yield self[part]

    def items(self) -> Iterator[tuple[Hashable, Graph | FrozenGraph]]:
        for part in self.parts:
            yield part, self[part]

    def __repr__(self) -> str:
        return (
            f"<SubgraphView with {len(self.parts)} and {len(self.subgraphs_cache)} cached graphs>"
        )
