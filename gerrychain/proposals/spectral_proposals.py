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
    nlist = list(graph.nodes())
    n = len(nlist)

    if weight_type == "random":
        for edge in graph.edge_indices:
            graph.edges[edge]["weight"] = random.random()

    # frm: The laplacian matrix is actually not all that complicated.  It
    #       is just the Degree matrix (diagonal matrix with degree of node
    #       as the diagonal value) minus the Adjacency matrix which 
    #       records for each (i,j) whether there is an edge between the
    #       two nodes i and j.  
    #
    #       However, I have no idea why the laplacian matrix is useful
    #       for GerryChain...
    #
    #       However, the normalized laplacian matrix IS complicated.
    #       It occurs to me that since we have access to the NetworkX
    #       code, we could just copy it - my guess is that it does not
    #       depend on specifics of the NetworkX implementation much...
    #
    #       Another option in the short term is to convert the rxgraph
    #       back into a nxgraph for the purposes of doing the laplacian
    #       and then converting it back.  I am not sure that we would 
    #       need to convert it back - does anyone else ever care about
    #       the weights that were assigned?  In any event, this would
    #       allow us to proceed (for now) without having to reimplement
    #       the laplacian functions to work on an rxgraph.
    #
    #       Note that since my frm_regresion.py test relies on recom
    #       not spectral_recom, I could just punt on this altogether for
    #       now, and just have this raise an exception saying "Not Yet Implemented"
    

    
    # frm TODO: Find a replacement for laplacian functions for a RustworkX graph...
    #
    #           Also - need to document what todense() does.  It is a SciPy function
    #           that converts a sparse matrix into its dense representation as a NumPy matrix.
    #           So, this is just a way to get a NumPy matrix for the laplacian (or normalized_laplacian).
    #
    #
    #           Note that while the standard laplacian is straight forward mathematically
    #           the normalized laplacian is a good bit more complicated.  However, since 
    #           NetworkX is open source - perhaps we can get permission to just use their
    #           code to create RX versions...

    if lap_type == "normalized":
        LAP = (nx.normalized_laplacian_matrix(graph)).todense()

    else:
        LAP = (nx.laplacian_matrix(graph)).todense()

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

    subgraph = partition.graph.subgraph(
        partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]
    )

    flips = spectral_cut(subgraph, parts_to_merge, weight_type, lap_type)

    return partition.flip(flips)
