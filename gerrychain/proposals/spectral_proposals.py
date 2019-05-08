import networkx as nx
from numpy import linalg as LA
from ..random import random


def spectral_cut(graph, part_labels, weight_type, lap_type):
    """Spectral cut function.

    Uses the signs of the elements in the Fiedler vector of a graph to
    partition into two components.

    """

    nlist = list(graph.nodes())
    n = len(nlist)

    if weight_type == "random":
        for edge in graph.edges():
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


def spectral_recom(partition, weight_type=None, lap_type="normalized"):
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

    """

    edge = random.choice(tuple(partition["cut_edges"]))
    parts_to_merge = (partition.assignment[edge[0]], partition.assignment[edge[1]])

    subgraph = partition.graph.subgraph(
        partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
    )

    flips = spectral_cut(
        subgraph,
        parts_to_merge,
        weight_type,
        lap_type
    )

    return partition.flip(flips)
