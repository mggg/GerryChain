import enum

try:
    import libpysal
except ImportError:
    try:
        import pysal.lib as libpysal
    except ImportError:
        import pysal as libpysal


class Adjacency(enum.Enum):
    """There are two concepts of "adjacency" that one can apply when constructing
    an adjacency graph.

    - **Rook adjacency**: Two polygons are adjacent if they share one or more *edges*.
    - **Queen adjacency**: Two polygons are adjacent if they share one or more *vertices*.

    All Rook edges are Queen edges, but not the other way around. Many congressional
    districts are only Queen-contiguous (i.e., they consist of two polygons connected
    at a single corner).

    The names Rook and Queen come from the way Rook and Queen pieces in Chess_ are
    allowed to move about the board.

    .. _Chess: https://en.wikipedia.org/wiki/Chess
    """

    Rook = "rook"
    Queen = "queen"


class UnrecognizedAdjacencyError(Exception):
    pass


adjacencies = {
    "rook": libpysal.weights.Rook,
    "queen": libpysal.weights.Queen,
    Adjacency.Rook: libpysal.weights.Rook,
    Adjacency.Queen: libpysal.weights.Queen,
}


def get_neighbors(df, adjacency):
    if not isinstance(adjacency, libpysal.weights.W):
        try:
            adjacency = adjacencies[adjacency]
        except KeyError:
            raise UnrecognizedAdjacencyError(
                "The adjacency parameter provided is not supported. Note: If you wish "
                "to use spatial weights other than Rook or Queen, you may pass any "
                "pysal weight (e.g., libpysal.weights.KNN for K-nearest neighbors) as "
                "the adjacency parameter."
            )
    return adjacency.from_dataframe(df).neighbors
