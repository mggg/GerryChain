import networkx as nx       # frm: only used to get access to laplacian functions...
from numpy import linalg as LA
import random
from ..graph import Graph
from ..partition import Partition
from typing import Dict, Optional

# frm: only ever used in this file - but maybe it is used externally?
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

    # frm:  Bad variable names - nlist is node_list and n is num_nodes   
    # frm: Original Code:   nlist = list(graph.nodes())
    # frm: TODO:  Subtle issue here - in NX there is no difference between a node ID
    #               and a node index (what you use to get a node from a list), but 
    #               in RX there is a difference - which manifests most in subgraphs
    #               where RX goes ahead and renumbers the nodes in the graph.  To
    #               make subgraphs work, we remember (in a map) what the node "IDs"
    #               of the parent graph were.
    #
    #               The issue here is what the code wants here.  We are in an RX 
    #               world at this point - so maybe it doesn't matter, but worth 
    #               thinking about...
    nlist = list(graph.nodes)
    n = len(nlist)

    if weight_type == "random":
        for edge_id in graph.edge_indices:
            # frm: Original Code:    graph.edges[edge]["weight"] = random.random()
            # frm: TODO: edges vs. edge_ids:  edge_ids are wanted here (integers)
            graph.edge_data(edge_id)["weight"] = random.random()

    # frm TODO: NYI: normalized_laplacian_matrix() for RX
    #
    #           Note that while the standard laplacian is straight forward mathematically
    #           the normalized laplacian is a good bit more complicated.  However, since 
    #           NetworkX is open source - perhaps we can get permission to just use their
    #           code to create RX versions...

    # Compute the desired laplacian matrix (convert from sparse to dense)
    if lap_type == "normalized":
        LAP = (graph.normalized_laplacian_matrix()).todense()
    else:
        LAP = (graph.laplacian_matrix()).todense()

    # frm TODO: Add comments and better names here.  
    #
    #           the LA.eigh(LAP) call below invokes the eigh() function from 
    #           the Numpy LinAlg module which "returns the eigenvalues and eigenvectors
    #           of a complex Hermitian ... or a real symmetrix matrix."  In our case
    #           we have a symmetric matrix.  It returns two objects - a 1-D array containing
    #           the eigenvalues and a 2-D square matrix of the eigenvectors.
    #
    #           So, again, better names and some comments please - such as a link to
    #           a URL that explains WTF this really does...

    NLMva, NLMve = LA.eigh(LAP)
    NFv = NLMve[:, 1]
    xNFv = [NFv.item(x) for x in range(n)]

    node_color = [xNFv[x] > 0 for x in range(n)]

    clusters = {nlist[x]: part_labels[node_color[x]] for x in range(n)}

    # frm: ???: TODO:   Why are these called "clusters" when the calling function
    #                   assigns them to "flips".  If they are flips, then shouldn't
    #                   they be named "flips"?
    return clusters


# frm: only ever used in this file - but maybe it is used externally?
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

    # frm ???:  I do not yet grok what this does at the code level...

    edge = random.choice(tuple(partition["cut_edges"]))
    parts_to_merge = (
        partition.assignment.mapping[edge[0]],
        partition.assignment.mapping[edge[1]],
    )

    # frm: TODO:  Does this code do the right thing for RX - where node_ids in subgraph change?
    subgraph = partition.graph.subgraph(
        partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
    )

    flips = spectral_cut(subgraph, parts_to_merge, weight_type, lap_type)

    return partition.flip(flips)
