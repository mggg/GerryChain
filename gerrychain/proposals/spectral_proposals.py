import networkx as nx       # frm: only used to get access to laplacian functions...
from numpy import linalg as LA
import random
from ..graph import Graph
from ..partition import Partition
from typing import Dict, Optional

# frm: only ever used in this file - but maybe it is used externally?
def spectral_cut(
    subgraph: Graph, part_labels: Dict, weight_type: str, lap_type: str
) -> Dict:
    """
    Spectral cut function.

    Uses the signs of the elements in the Fiedler vector of a subgraph to
    partition into two components.

    :param subgraph: The subgraph to be partitioned.
    :type subgraph: Graph
    :param part_labels: The current partition of the subgraph.
    :type part_labels: Dict
    :param weight_type: The type of weight to be used in the Laplacian.
    :type weight_type: str
    :param lap_type: The type of Laplacian to be used.
    :type lap_type: str

    :returns: A dictionary assigning nodes of the subgraph to their new districts.
    :rtype: Dict
    """

    # This routine operates on subgraphs, which is important because the node_ids
    # in a subgraph are different from the node_ids of the parent graph, so 
    # the return value's node_ids need to be translated back into the appropriate
    # parent node_ids.

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
    node_list = list(subgraph.nodes)
    num_nodes = len(node_list)

    if weight_type == "random":
        # assign a random weight to each edge in the subgraph
        for edge_id in subgraph.edge_indices:
            subgraph.edge_data(edge_id)["weight"] = random.random()

    # frm TODO: NX vs. RX Issue:   NYI: normalized_laplacian_matrix() for RX
    #
    #           Note that while the standard laplacian is straight forward mathematically
    #           the normalized laplacian is a good bit more complicated.  However, since 
    #           NetworkX is open source - perhaps we can get permission to just use their
    #           code to create RX versions...

    # Compute the desired laplacian matrix (convert from sparse to dense)
    if lap_type == "normalized":
        laplacian_matrix = (subgraph.normalized_laplacian_matrix()).todense()
    else:
        laplacian_matrix = (subgraph.laplacian_matrix()).todense()

    # frm TODO: Add a better explanation for why eigenvectors are useful
    #           for determining flips.  Perhaps just a URL to an article 
    #           somewhere...
    #
    # I have added comments to describe the nuts and bolts of what is happening,
    # but the overall rationale for this code is missing - and it should be here...


    # LA.eigh(laplacian_matrix) call invokes the eigh() function from 
    # the Numpy LinAlg module which:
    #
    #     "returns the eigenvalues and eigenvectors of a complex Hermitian 
    #      ... or a real symmetrix matrix."  
    #
    # In our case we have a symmetric matrix, so it returns two 
    # objects - a 1-D numpy array containing the eigenvalues (which we don't
    # care about) and a 2-D numpy square matrix of the eigenvectors.
    numpy_eigen_values, numpy_eigen_vectors = LA.eigh(laplacian_matrix)

    # Extract an eigenvector as a numpy array
    # frm: ???:  Not sure why we want just one of them...
    numpy_eigen_vector = numpy_eigen_vectors[:, 1]    # frm: ??? I think that this is an eigenvector...

    # Convert to an array of normal Python numbers (not numpy based)
    eigen_vector_array = [numpy_eigen_vector.item(x) for x in range(num_nodes)]

    # node_color will be True or False depending on whether the value in the
    # eigen_vector_array is positive or negative.  In the code below, this 
    # is equivalent to node_color being 1 or 0 (since Python treats True as 1 
    # and False as 0)
    node_color = [eigen_vector_array[x] > 0 for x in range(num_nodes)]

    # Create flips using the node_color to select which part (district) to assign
    # to the node.
    flips = {node_list[x]: part_labels[node_color[x]] for x in range(num_nodes)}

    # translate subgraph node_ids in flips to parent_graph node_ids
    translated_flips = subgraph.translate_subgraph_node_ids_for_flips(flips)

    return translated_flips


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

    # Select two adjacent parts (districts) at random by first selecting 
    # a cut_edge at random and then figuring out the parts (districts) 
    # associated with the edge.
    cut_edge = random.choice(tuple(partition["cut_edges"]))
    parts_to_merge = (
        partition.assignment.mapping[cut_edge[0]],  
        partition.assignment.mapping[cut_edge[1]],
    )

    subgraph_nodes = partition.parts[parts_to_merge[0]] | partition.parts[parts_to_merge[1]]

    # Cut the set of all nodes from parts_to_merge into two hopefully new parts (districts)
    flips = spectral_cut(
      partition.graph.subgraph(subgraph_nodes),
      parts_to_merge, 
      weight_type, 
      lap_type
    )

    return partition.flip(flips)
