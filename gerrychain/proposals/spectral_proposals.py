import random
from collections.abc import Hashable, Sequence
from functools import partial
from typing import cast

from numpy import linalg as LA

from .._rng import make_rng
from ..graph import FrozenGraph, Graph
from ..partition import Partition
from ..proposals import ProposalFn


# frm: only ever used in this file - but maybe it is used externally?
def spectral_cut(
    subgraph: Graph | FrozenGraph,
    part_labels: Sequence[Hashable],
    weight_type: str | None,
    lap_type: str,
    *,
    rng: random.Random | int | None = None,
) -> dict[Hashable, Hashable]:
    """Spectral cut function.

    Original templates and work from Daryl DeFord:

        https://github.com/drdeford/GerryChain-Templates

    New preprint on the subject:

        https://arxiv.org/html/2506.13982v1

    Args:
        subgraph (Graph): The subgraph to be partitioned.
        part_labels (Sequence[Hashable]): The current partition of the subgraph.
        weight_type (str | None): The type of weight to be used in the Laplacian.
        lap_type (str): The type of Laplacian to be used.
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        dict[Hashable, Hashable]: A dictionary assigning nodes of the subgraph to their new
            districts.
    """

    rng = make_rng(rng)

    # This routine operates on subgraphs, which is important because the node_ids
    # in a subgraph are different from the node_ids of the parent graph, so
    # the return value's node_ids need to be translated back into the appropriate
    # parent node_ids.

    node_list = list(subgraph.node_indices)
    num_nodes = len(node_list)

    if weight_type == "random":
        # assign a random weight to each edge in the subgraph
        for edge_id in subgraph.edge_indices:
            subgraph.edge_data(edge_id)["weight"] = rng.random()

    # Compute the desired laplacian matrix (convert from sparse to dense)
    if lap_type == "normalized":
        laplacian_matrix = (subgraph.normalized_laplacian_matrix()).todense()
    else:
        laplacian_matrix = (subgraph.laplacian_matrix()).todense()

    # Note:
    #
    # LA.eigh(laplacian_matrix) call invokes the eigh() function from
    # the Numpy LinAlg module which:
    #
    #     "returns the eigenvalues and eigenvectors of a complex Hermitian
    #      ... or a real symmetrix matrix."
    #
    # In our case we have a symmetric matrix, so it returns two
    # objects - a 1-D numpy array containing the eigenvalues (which we don't
    # care about) and a 2-D numpy square matrix of the eigenvectors.

    _, numpy_eigen_vectors = LA.eigh(laplacian_matrix)

    # Extract an eigenvector as a numpy array
    # frm: ???:  Not sure why we want just one of them...
    numpy_eigen_vector = numpy_eigen_vectors[
        :, 1
    ]  # frm: ??? I think that this is an eigenvector...

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
    weight_type: str | None = None,
    lap_type: str = "normalized",
    *,
    rng: random.Random | int | None = None,
) -> Partition:
    """Spectral ReCom proposal.

    Uses spectral clustering to bipartition a subgraph of the original graph formed by merging the
    nodes corresponding to two adjacent districts.

    Example usage::

        from functools import partial from gerrychain import MarkovChain from gerrychain.proposals
        import recom

        # ...define constraints, accept, partition, total_steps here...

        proposal = partial( spectral_recom, weight_type=None, lap_type="normalized" )

        chain = MarkovChain(proposal, constraints, accept, partition, total_steps)

    Args:
        partition (Partition): The initial partition.
        weight_type (str | None, optional): The type of weight to be used in the Laplacian.
            Default is None.
        lap_type (str, optional): The type of Laplacian to be used. Default is "normalized".
        rng (random.Random | int | None, optional): Source of randomness. Pass a shared
            ``Random`` for repeated standalone calls; an integer restarts the stream each call.

    Returns:
        Partition: The new partition resulting from the spectral ReCom algorithm.
    """

    rng = make_rng(rng)

    # Select two adjacent parts (districts) at random by first selecting
    # a cut_edge at random and then figuring out the parts (districts)
    # associated with the edge.
    cut_edge = rng.choice(tuple(partition["cut_edges"]))
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
        lap_type,
        rng=rng,
    )

    return partition.flip(flips)


# Define a ProposalFn version to make purpose of the function clear
def build_spectral_recom_proposal_fn(
    weight_type: str | None = None,
    lap_type: str = "normalized",
) -> ProposalFn:
    proposal_fn = partial(spectral_recom, weight_type=weight_type, lap_type=lap_type)
    return cast(ProposalFn, proposal_fn)
