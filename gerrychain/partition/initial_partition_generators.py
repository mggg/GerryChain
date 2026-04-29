from functools import partial
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Union,
)

# frm:  import the new Graph object which encapsulates NX and RX Graph...
from ..graph import Graph
from ..tree import BalanceError, PopulationBalanceError, bipartition_tree

"""
This module provides routines to create initial assignments for a Partition object.

In particular, it defines two functions, recursive_tree_part() and recursive_seed_part().

The recursive_seed_part() function uses a divide and conquer approach which avoids the
potential problem that recursive_tree_part() has where it sometimes paints itself into
a corner.

There are 2 main issues with the recursive_tree_part that appear when you are trying
to subdivide into a large number of districts that the seed part method solves

  1. recursive_tree_part only carves off one district at a time, but since each of
     the districts are approximately population balanced, you need to dynamically
     adjust the target range as you carve things off. If you cut off something
     slightly larger than ideal, then adjust the target for the next district
     down, and visa versa. This sort of bookeeping is a bit tricky, and, if the
     allowable population band is too large, can end up with you getting stuck.

  2.Since recursive_tree_part only carves off one district at a time, if there
    are a lot of districts to cut off, you can cut off districts in such a way
    that the remaining graph is impossible to population balance. This is mostly
    caused by cutting off districts in a "snake-y" way so as to leave very small
    bits of unassigned graphs (with possibly high nodes population) between
    assigned areas. In the abstract, you can imagine that you produce something
    very close to a path with the following populations:

4 - 10 - 12 - 8

There is no way to subdivide this graph into 2 pieces of even size. In fact,
you can't even get within 10% population tolerance (17 +/- 1.7).

The recursive_seed_part method keeps this from happening so much by biting off
large, approximately balanced things, and then recursing inward. Under this
schema, it's a lot harder to make a snake-y patchwork of districts.

"""


def recursive_tree_part(
    graph: Graph,
    parts: Sequence,
    pop_target: Union[float, int],
    pop_col: str,
    epsilon: float,
    node_repeats: int = 1,
    bipartition_tree_fn: Callable = partial(bipartition_tree, max_attempts=100000),
) -> Dict:
    """Return new assignments for the nodes of ``graph``.

    Uses `gerrychain.tree.bipartition_tree` recursively to partition a tree into
    ``len(parts)`` parts of population ``pop_target`` (within ``epsilon``).

    Can be used to generate initial seed plans (partition assignments) or to implement ReCom-like
    "merge walk" proposals.

    Args:
        graph (Graph): The graph to partition into ``len(parts)`` :math:`\varepsilon`-balanced
            parts.
        parts (Sequence): Iterable of part (district) labels (like ``[0,1,2]`` or ``range(4)``).
        pop_target (Union[float, int]): Target population for each part of the partition.
        pop_col (str): Node attribute key holding population data.
        epsilon (float): How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
            of the partition can be.
        node_repeats (int, optional): Parameter for `gerrychain.tree.bipartition_tree` to
            use. Defaluts to 1.
        bipartition_tree_fn (Callable, optional): The partition method to use. Defaults to
            `partial(bipartition_tree, max_attempts=100000)`.

    Returns:
        dict: New assignments for the nodes of ``graph``.
    """

    flips = {}
    remaining_nodes = graph.node_indices

    # We keep a running tally of deviation from ``epsilon`` at each partition
    # and use it to tighten the population constraints on a per-partition
    # basis such that every partition, including the last partition, has a
    # population within +/-``epsilon`` of the target population.
    # For instance, if district n's population exceeds the target by 2%
    # with a +/-2% epsilon, then district n+1's population should be between
    # 98% of the target population and the target population.
    debt: Union[int, float] = 0

    lb_pop = pop_target * (1 - epsilon)
    ub_pop = pop_target * (1 + epsilon)
    check_pop = lambda x: lb_pop <= x <= ub_pop

    # The code in the for-loop creates n-2 districts (where n is
    # the number of partitions desired) by calling the "bipartition_tree_fn"
    # function, whose job it is to produce a connected set of
    # nodes that has the desired population target.
    #
    # Note that it sets one_sided_cut=True which tells the
    # "bipartition_tree_fn" function that it is NOT bisecting the graph
    # but is rather supposed to just find one connected
    # set of nodes of the correct population size.

    for part in parts[:-2]:
        min_pop = max(pop_target * (1 - epsilon), pop_target * (1 - epsilon) - debt)
        max_pop = min(pop_target * (1 + epsilon), pop_target * (1 + epsilon) - debt)
        new_pop_target = (min_pop + max_pop) / 2

        try:
            node_ids = bipartition_tree_fn(
                graph.subgraph(remaining_nodes),
                pop_col=pop_col,
                pop_target=new_pop_target,
                epsilon=(max_pop - min_pop) / (2 * new_pop_target),
                node_repeats=node_repeats,
                one_sided_cut=True,
            )
        except Exception:
            raise

        if node_ids is None:
            raise BalanceError()

        part_pop = 0
        for node_id in node_ids:
            flips[node_id] = part
            part_pop += graph.node_data(node_id)[pop_col]

        if not check_pop(part_pop):
            raise PopulationBalanceError()

        debt += part_pop - pop_target
        remaining_nodes -= node_ids

    # After making n-2 districts, we need to make sure that the last
    # two districts are both balanced.

    # For the last call to "bipartition_tree_fn", set one_sided_cut=False to
    # request that "bipartition_tree_fn" create two equal sized districts
    # with the given population goal by bisecting the graph.
    node_ids = bipartition_tree_fn(
        graph.subgraph(remaining_nodes),
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        one_sided_cut=False,
    )

    if node_ids is None:
        raise BalanceError()

    part_pop = 0
    for node_id in node_ids:
        flips[node_id] = parts[-2]
        part_pop += graph.node_data(node_id)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    remaining_nodes -= node_ids

    # All of the remaining nodes go in the last part
    part_pop = 0
    for node in remaining_nodes:
        flips[node] = parts[-1]
        part_pop += graph.node_data(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    return flips


def _get_seed_chunks(
    graph: Graph,
    num_chunks: int,
    num_dists: int,
    pop_target: Union[int, float],
    pop_col: str,
    epsilon: float,
    node_repeats: int = 1,
    bipartition_tree_fn: Callable = partial(bipartition_tree, max_attempts=100000),
) -> List[List[int]]:
    """Helper function for recursive_seed_part.

    Partitions the graph into ``num_chunks`` chunks, balanced within new_epsilon <= ``epsilon`` of
    a balanced target population.

    It calls the bipartition_tree_fn function repeatedly to create parts (districts).

    Args:
        graph (Graph): The graph
        num_chunks (int): The number of chunks to partition the graph into
        num_dists (int): The number of districts
        pop_target (Union[int, float]): The target population of the districts (not of the chunks)
        pop_col (str): Node attribute key holding population data
        epsilon (float): How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
            of the partition can be
        node_repeats (int, optional): Parameter for `gerrychain.tree.bipartition_tree` to
            use. Defaults to 1.
        bipartition_tree_fn (Callable, optional): The method to use for bipartitioning the graph.
            Defaults to `gerrychain.tree.bipartition_tree`

    Returns:
        List[List[int]]: New assignments for the nodes of ``graph``.
    """

    if num_dists % num_chunks != 0:
        raise Exception(
            "_get_seed_chunks: internal error: num_chunks does not evenly divide num_dists"
        )

    num_districts_per_chunk = num_dists // num_chunks

    # Create a list of names (integers) for each of the parts (districts) we will create.
    parts = range(num_chunks)
    # frm: ???: I think that new_epsilon is the epsilon to use for each district, in which
    #           case the epsilon passed in would be for the  HERE...
    new_epsilon = epsilon / (num_districts_per_chunk * num_chunks)
    if num_districts_per_chunk == 1:
        new_epsilon = epsilon

    chunk_pop = 0
    for node in graph.node_indices:
        chunk_pop += graph.node_data(node)[pop_col]

    while True:
        epsilon = abs(epsilon)

        flips = {}
        remaining_nodes = graph.node_indices

        # frm: ??? What is the distinction between num_chunks and num_districts?
        #           I think that a chunk is typically a multiple of districts, so
        #           if we want 15 districts we might only ask for 5 chunks.  Stated
        #           differently a chunk will always have at least enough nodes
        #           for a given number of districts.  As the chunk size gets
        #           smaller, the number of nodes more closely matches what
        #           is needed for a set number of districts.

        # frm: Note:  This just scales epsilon by the number of districts for each chunk
        #               so we can get chunks with the appropriate population sizes...
        min_pop = pop_target * (1 - new_epsilon) * num_districts_per_chunk
        max_pop = pop_target * (1 + new_epsilon) * num_districts_per_chunk

        chunk_pop_target = chunk_pop / num_chunks

        diff = min(max_pop - chunk_pop_target, chunk_pop_target - min_pop)
        new_new_epsilon = diff / chunk_pop_target

        # frm: Note:  This code is clever...  It loops through all of the
        #               parts (districts) except the last, and on each
        #               iteration, it finds nodes for the given part.
        #               Each time through the loop it assigns the
        #               unassigned nodes to the last part, but
        #               most of this gets overwritten by the next
        #               iteration, so that at the end the only nodes
        #               still assigned to the last part are the ones
        #               that had not been previously assigned.
        #
        #               It works, but is a little too clever for me.
        #
        #               I would just have assigned all nodes to
        #               the last part before entering the loop
        #               with a comment saying that by end of loop
        #               the nodes not assigned in the loop will
        #               default to the last part.
        #

        # Assign all nodes to one of the parts (districts)
        for i in range(len(parts[:-1])):
            part = parts[i]

            nodes = bipartition_tree_fn(
                graph.subgraph(remaining_nodes),
                pop_col=pop_col,
                pop_target=chunk_pop_target,
                epsilon=new_new_epsilon,
                node_repeats=node_repeats,
            )

            if nodes is None:
                raise BalanceError()

            for node in nodes:
                flips[node] = part
            remaining_nodes -= nodes

            # All of the remaining nodes go in the last part
            for node in remaining_nodes:
                flips[node] = parts[-1]

        # frm: ???: Look at remaining_nodes to see if we are done
        part_pop = 0
        # frm: ???: Compute population total for remaining nodes.
        for node in remaining_nodes:
            part_pop += graph.node_data(node)[pop_col]
        # frm: ???: Compute what the population total would be for each district in chunk
        part_pop_as_dist = part_pop / num_districts_per_chunk
        fake_epsilon = epsilon
        # frm: ???: If the chunk is for more than one district, divide epsilon by two
        if num_districts_per_chunk != 1:
            fake_epsilon = epsilon / 2
        # frm: ???:  Calculate max and min populations on a district level
        #               This will just be based on epsilon if we only want one district from
        #               chunk, but it will be based on half of epsilon if we want more than one
        #               district from chunk. This is odd - why wouldn't we use an epsilon
        min_pop_as_dist = pop_target * (1 - fake_epsilon)
        max_pop_as_dist = pop_target * (1 + fake_epsilon)

        if part_pop_as_dist < min_pop_as_dist:
            new_epsilon = new_epsilon / 2
        elif part_pop_as_dist > max_pop_as_dist:
            new_epsilon = new_epsilon / 2
        else:
            break

    chunks: Dict[Any, List] = {}
    for key in flips.keys():
        if flips[key] not in chunks.keys():
            chunks[flips[key]] = []
        chunks[flips[key]].append(key)

    return list(chunks.values())


# frm: only used in this file
#       But maybe this is intended to be used externally...
def get_max_prime_factor_less_than(n: int, ceil: int) -> Optional[int]:
    """Helper function for _recursive_seed_part_inner.

    Returns the largest prime factor of ``n`` less than ``ceil``, or None if all are greater than
    ceil.

    Args:
        n (int): The number to find the largest prime factor for.
        ceil (int): The upper limit for the largest prime factor.

    Returns:
        Optional[int]: The largest prime factor of ``n`` less than ``ceil``, or None if all are
            greater than ceil.
    """
    if n <= 1 or ceil <= 1:
        return None

    largest_factor = None
    while n % 2 == 0:
        largest_factor = 2
        n //= 2

    i = 3
    while i * i <= n:
        while n % i == 0:
            if i <= ceil:
                largest_factor = i
            n //= i
        i += 2

    if n > 1 and n <= ceil:
        largest_factor = n

    return largest_factor


def _recursive_seed_part_inner(
    graph: Graph,
    num_dists: int,
    pop_target: Union[float, int],
    pop_col: str,
    epsilon: float,
    bipartition_tree_fn: Callable = partial(bipartition_tree, max_attempts=100000),
    node_repeats: int = 1,
    n: Optional[int] = None,
    ceil: Optional[int] = None,
) -> List[Set]:
    """Inner function for recursive_seed_part.

    Returns a list of sets of nodes with ``num_dists`` districts balanced within ``epsilon`` of
    ``pop_target``.

    This list of sets of nodes is conceptually equivalent to an Assignment object. Each set of
    nodes constitutes a district, but the district does not have an ID, and there is nothing that
    associates these nodes with a specific graph - that is implicit, depending on the graph object
    passed in, so the caller is responsible for knowing that the returned list of sets belongs to
    the graph passed in...

    It splits the graph into num_chunks chunks, and then recursively splits each chunk into
    ``num_dists``/num_chunks chunks. The number num_chunks of chunks is chosen based on ``n`` and
    ``ceil`` as follows:

    - If ``n`` is None, and ``ceil`` is None, num_chunks is the largest prime factor of
    ``num_dists``. - If ``n`` is None and ``ceil`` is an integer at least 2, then num_chunks is the
    largest prime factor of ``num_dists`` that is less than ``ceil`` - If ``n`` is a positive
    integer, num_chunks equals n.

    Finally, if the number of chunks as chosen above does not divide ``num_dists``, then this
    function bites off a single district from the graph and recursively partitions the remaining
    graph into ``num_dists - 1`` districts.

    Args:
        graph (Graph): The underlying graph structure.
        num_dists (int): number of districts to partition the graph into
        pop_target (Union[float, int]): Target population for each part of the partition
        pop_col (str): Node attribute key holding population data
        epsilon (float): How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
            of the partition can be
        bipartition_tree_fn (Callable, optional): Function used to find balanced partitions at the
            2-district level. Defaults to `gerrychain.tree.bipartition_tree`
        node_repeats (int, optional): Parameter for `gerrychain.tree.bipartition_tree` to
            use. Defaults to 1.
        n (Optional[int], optional): Either a positive integer (greater than 1) or None. If n is a
            positive integer, this function will recursively create a seed plan by either biting
            off districts from graph or dividing graph into n chunks and recursing into each of
            these. If n is None, this function prime factors ``num_dists``=n_1*n_2*...*n_k (n_1 >
            n_2 > ... n_k) and recursively partitions graph into n_1 chunks. Defaults to None.
        ceil (Optional[int], optional): Either a positive integer (at least 2) or None. Relevant
            only if n is None. If ``ceil`` is a positive integer then finds the largest factor of
            ``num_dists`` less than or equal to ``ceil``, and recursively splits graph into that
            number of chunks, or bites off a district if that number is 1. Defaults to None.

    Returns:
        List of sets, each set is a district: New assignments for the nodes of ``graph``.
    """

    # Chooses num_chunks
    if n is None:
        if ceil is None:
            num_chunks = get_max_prime_factor_less_than(num_dists, num_dists)
        elif ceil >= 2:
            num_chunks = get_max_prime_factor_less_than(num_dists, ceil)
        else:
            raise ValueError("ceil must be None or at least 2")
    elif n > 1:
        # frm: Note: This is not guaranteed to evenly divide num_dists
        num_chunks = n
    else:
        raise ValueError("n must be None or a positive integer")

    # base case
    if num_dists == 1:
        # Just return an assignment with all of the nodes in the graph

        # Translate the node_ids into parent_node_ids
        translated_set_of_nodes = graph.translate_subgraph_node_ids_for_set_of_nodes(
            graph.node_indices
        )
        translated_assignment = []
        translated_assignment.append(translated_set_of_nodes)
        return translated_assignment

    # frm: In the case when there are exactly 2 districts, split the graph by setting
    #       one_sided_cut to be False.
    if num_dists == 2:
        nodes = bipartition_tree_fn(
            graph.subgraph(graph.node_indices),  # needs to be a subgraph
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            node_repeats=node_repeats,
            one_sided_cut=False,  # flag to say we want to bisect graph
        )

        nodes_for_one_district = set(nodes)
        nodes_for_the_other_district = set(graph.node_indices) - nodes_for_one_district

        # Translate the subgraph node_ids into parent_node_ids
        translated_set_1 = graph.translate_subgraph_node_ids_for_set_of_nodes(
            nodes_for_one_district
        )
        translated_set_2 = graph.translate_subgraph_node_ids_for_set_of_nodes(
            nodes_for_the_other_district
        )

        return [translated_set_1, translated_set_2]

    # bite off a district and recurse into the remaining subgraph
    # frm: Note:  In the case when num_chunks does not evenly divide num_dists,
    #               just find one district, remove those nodes from
    #               the unassigned nodes and try again with num_dists
    #               set to be one less.  Stated differently, reduce
    #               number of desired districts until you get to
    #               one that is evenly divided by num_chunks and then
    #               do chunk stuff...
    elif num_chunks is None or num_dists % num_chunks != 0:
        remaining_nodes = graph.node_indices
        nodes = bipartition_tree_fn(
            graph.subgraph(remaining_nodes),
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            node_repeats=node_repeats,
            one_sided_cut=True,
        )
        remaining_nodes -= nodes
        # frm: Create a list with the set of nodes returned by
        # bipartition_tree_fn() and then recurse
        #       to get the rest of the sets of nodes for remaining districts.
        assignment = [nodes] + _recursive_seed_part_inner(
            graph.subgraph(remaining_nodes),
            num_dists - 1,
            pop_target,
            pop_col,
            epsilon,
            bipartition_tree_fn,
            n=n,
            ceil=ceil,
        )

    # split graph into num_chunks chunks, and recurse into each chunk
    elif num_dists % num_chunks == 0:
        chunks = _get_seed_chunks(
            graph.subgraph(graph.node_indices),  # needs to be a subgraph
            num_chunks,
            num_dists,
            pop_target,
            pop_col,
            epsilon,
            bipartition_tree_fn=partial(bipartition_tree_fn, one_sided_cut=True),
        )

        assignment = []
        for chunk in chunks:
            chunk_assignment = _recursive_seed_part_inner(
                graph.subgraph(chunk),
                num_dists // num_chunks,  # new target number of districts
                pop_target,
                pop_col,
                epsilon,
                bipartition_tree_fn,
                n=n,
                ceil=ceil,
            )
            assignment += chunk_assignment
    else:
        # frm: From the logic above, this should never happen, but if it did
        #       because of a future edit (bug), at least this will catch it
        #       early before really bizarre things happen...
        raise Exception("_recursive_seed_part_inner(): Should never happen...")

    # The assignment object that has been created needs to have its
    # node_ids translated into parent_node_ids

    translated_assignment = []
    for set_of_nodes in assignment:
        translated_set_of_nodes = graph.translate_subgraph_node_ids_for_set_of_nodes(set_of_nodes)
        translated_assignment.append(translated_set_of_nodes)

    return translated_assignment


def recursive_seed_part(
    graph: Graph,
    parts: Sequence,
    pop_target: Union[float, int],
    pop_col: str,
    epsilon: float,
    bipartition_tree_fn: Callable = partial(bipartition_tree, max_attempts=100000),
    node_repeats: int = 1,
    n: Optional[int] = None,
    ceil: Optional[int] = None,
) -> Dict:
    """Returns an assignment dictionary with ``num_dists`` districts balanced within ``epsilon``.

    Returns an assignment dictionary with ``num_dists`` districts balanced within ``epsilon`` of.
    ``pop_target`` by recursively splitting graph using _recursive_seed_part_inner.

    Args:
        graph (Graph): The graph
        parts (Sequence): Iterable of part labels (like ``[0,1,2]`` or ``range(4)``
        pop_target (Union[float, int]): Target population for each part of the partition
        pop_col (str): Node attribute key holding population data
        epsilon (float): How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
            of the partition can be
        bipartition_tree_fn (Callable, optional): Function used to find balanced partitions at the
            2-district level Defaults to `gerrychain.tree.bipartition_tree`
        node_repeats (int, optional): Parameter for `gerrychain.tree.bipartition_tree` to
            use. Defaults to 1.
        n (Optional[int], optional): Either a positive integer (greater than 1) or None. If n is a
            positive integer, this function will recursively create a seed plan by either biting
            off districts from graph or dividing graph into n chunks and recursing into each of
            these. If n is None, this function prime factors ``num_dists``=n_1*n_2*...*n_k (n_1 >
            n_2 > ... n_k) and recursively partitions graph into n_1 chunks. Defaults to None.
        ceil (Optional[int], optional): Either a positive integer (at least 2) or None. Relevant
            only if n is None. If ``ceil`` is a positive integer then finds the largest factor of
            ``num_dists`` less than or equal to ``ceil``, and recursively splits graph into that
            number of chunks, or bites off a district if that number is 1. Defaults to None.

    Returns:
        dict: New assignments for the nodes of ``graph``.
    """

    # Note: recursive_seed_part() is never used in the GerryCode codebase, but it is
    # part of the public API.

    # frm: Note: It is not strictly necessary to use a subgraph in the call below on
    #               _recursive_seed_part_inner(), because the top-level graph has
    #               a _node_id_to_parent_node_id_map that just maps node_ids to themselves.
    #               However, it seemed a good practice to ALWAYS call routines that are intended
    #               to deal with subgraphs, to use a subgraph even when not strictly
    #               necessary.  Just one more cognitive load to not have to worry about.
    #
    #               This probably means that the identity _node_id_to_parent_node_id_map for
    #               top-level graphs will never be used, I still think that it makes sense to
    #               retain it - again, for consistency: Every graph knows how to translate to
    #               parent_node_ids even if it is a top-level graph.
    #
    #               In short - an argument based on invariants being a good thing...
    #
    flips = {}
    assignment = _recursive_seed_part_inner(
        graph.subgraph(graph.node_indices),
        len(parts),
        pop_target,
        pop_col,
        epsilon,
        bipartition_tree_fn=bipartition_tree_fn,
        node_repeats=node_repeats,
        n=n,
        ceil=ceil,
    )
    for i in range(len(assignment)):
        for node in assignment[i]:
            flips[node] = parts[i]
    return flips
