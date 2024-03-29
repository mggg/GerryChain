import networkx as nx
from numpy import linalg as LA
import random
from ..graph import Graph
from ..partition import Partition
from typing import Dict, Optional


def spectral_cut(
    graph: Graph, part_labels: Dict, weight_type: str, lap_type: str
) -> Dict:
    """
    Spectral cut function.

    Uses the signs of the elements in the Fiedler vector of a graph to
    partition into two components.

    :param graph: The graph to be partitioned.
    :type graph: Graph
    :param part_labels: The current partition of the graph.
    :type part_labels: Dict
    :param weight_type: The type of weight to be used in the Laplacian.
    :type weight_type: str
    :param lap_type: The type of Laplacian to be used.
    :type lap_type: str

    :returns: A dictionary assigning nodes of the graph to their new districts.
    :rtype: Dict
    """

    nlist = list(graph.nodes())
    n = len(nlist)

    if weight_type == "random":
        for edge in graph.edge_indices:
            graph.edges[edge]["weight"] = random.random()

    if lap_type == "normalized":
        LAP = (nx.normalized_laplacian_matrix(graph)).todense()

    else:
        LAP = (nx.laplacian_matrix(graph)).todense()

    NLMva, NLMve = LA.eigh(LAP)
    NFv = NLMve[:, 1]
    xNFv = [NFv.item(x) for x in range(n)]

    node_color = [xNFv[x] > 0 for x in range(n)]

    clusters = {nlist[x]: part_labels[node_color[x]] for x in range(n)}

    return clusters


def spectral_recom(
    partition: Partition,
    weight_type: Optional[str] = None,
    lap_type: str = "normalized",
) -> Partition:
    """Spectral ReCom proposal.

    Uses spectral clustering to bipartition a subgraph of the original graph
    formed by merging the nodes corresponding to two adjacent districts.

    Example usage::

        from functools import partial
        from gerrychain import MarkovChain
        from gerrychain.proposals import recom

        # ...define constraints, accept, partition, total_steps here...


        proposal = partial(
            spectral_recom, weight_type=None, lap_type="normalized"
        )

        chain = MarkovChain(proposal, constraints, accept, partition, total_steps)

    :param partition: The initial partition.
    :type partition: Partition
    :param weight_type: The type of weight to be used in the Laplacian. Default is None.
    :type weight_type: Optional[str], optional
    :param lap_type: The type of Laplacian to be used. Default is "normalized".
    :type lap_type: str, optional

    :returns: The new partition resulting from the spectral ReCom algorithm.
    :rtype: Partition
    """

    edge = random.choice(tuple(partition["cut_edges"]))
    parts_to_merge = (
        partition.assignment.mapping[edge[0]],
        partition.assignment.mapping[edge[1]],
    )

    subgraph = partition.graph.subgraph(
        partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
    )

    flips = spectral_cut(subgraph, parts_to_merge, weight_type, lap_type)

    return partition.flip(flips)
