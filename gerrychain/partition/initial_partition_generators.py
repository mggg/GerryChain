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
from ..tree import BalanceError, PopulationBalanceError, bipartition_tree, bipartition_tree_random

# frm: TODO: Update docstrings below
"""
This module provides routines to create initial assignments for a Partition object.

"""


# frm: TODO: Delete this note to Peter:
#
# Note to Peter:  param name, "method", has been changed everywhere to "bipartition_tree_fn"
#
# I have added a note to the rx_release_notes.md file that we should warn users about this
# change.


def recursive_tree_part(
    graph: Graph,
    parts: Sequence,
    pop_target: Union[float, int],
    pop_col: str,
    epsilon: float,
    node_repeats: int = 1,
    bipartition_tree_fn: Callable = partial(bipartition_tree, max_attempts=10000),
) -> Dict:
    """
    Uses :func:`~gerrychain.tree.bipartition_tree` recursively to partition a tree into
    ``len(parts)`` parts of population ``pop_target`` (within ``epsilon``). Can be used to
    generate initial seed plans (partition assignments) or to implement ReCom-like "merge walk" proposals.

    :param graph: The graph to partition into ``len(parts)`` :math:`\varepsilon`-balanced parts.
    :type graph: Graph
    :param parts: Iterable of part (district) labels (like ``[0,1,2]`` or ``range(4)``).
    :type parts: Sequence
    :param pop_target: Target population for each part of the partition.
    :type pop_target: Union[float, int]
    :param pop_col: Node attribute key holding population data.
    :type pop_col: str
    :param epsilon: How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
        of the partition can be.
    :type epsilon: float
    :param node_repeats: Parameter for :func:`~gerrychain.tree.bipartition_tree` to use.
        Defaluts to 1.
    :type node_repeats: int, optional
    :param bipartition_tree_fn: The partition method to use. Defaults to
        `partial(bipartition_tree, max_attempts=10000)`.
    :type bipartition_tree_fn: Callable, optional

    :returns: New assignments for the nodes of ``graph``.
    :rtype: dict
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

    # frm: Notes to self:  The code in the for-loop creates n-2 districts (where n is
    #                       the number of partitions desired) by calling the "bipartition_tree_fn"
    #                       function, whose job it is to produce a connected set of
    #                       nodes that has the desired population target.
    #
    #                       Note that it sets one_sided_cut=True which tells the
    #                       "bipartition_tree_fn" function that it is NOT bisecting the graph
    #                       but is rather supposed to just find one connected
    #                       set of nodes of the correct population size.

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

    # frm: For the last call to "bipartition_tree_fn", set one_sided_cut=False to
    #       request that "bipartition_tree_fn" create two equal sized districts
    #       with the given population goal by bisecting the graph.
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


# frm: only used in this file, so I changed the name to have a leading underscore
def _get_seed_chunks(
    graph: Graph,
    num_chunks: int,
    num_dists: int,
    pop_target: Union[int, float],
    pop_col: str,
    epsilon: float,
    node_repeats: int = 1,
    bipartition_tree_fn: Callable = partial(bipartition_tree_random, max_attempts=10000),
) -> List[List[int]]:
    """
    Helper function for recursive_seed_part. Partitions the graph into ``num_chunks`` chunks,
    balanced within new_epsilon <= ``epsilon`` of a balanced target population.

    :param graph: The graph
    :type graph: Graph
    :param num_chunks: The number of chunks to partition the graph into
    :type num_chunks: int
    :param num_dists: The number of districts
    :type num_dists: int
    :param pop_target: The target population of the districts (not of the chunks)
    :type pop_target: Union[int, float]
    :param pop_col: Node attribute key holding population data
    :type pop_col: str
    :param epsilon: How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
        of the partition can be
    :type epsilon: float
    :param node_repeats: Parameter for :func:`~gerrychain.tree.bipartition_tree_random`
        to use. Defaults to 1.
    :type node_repeats: int, optional
    :param bipartition_tree_fn: The method to use for bipartitioning the graph.
        Defaults to :func:`~gerrychain.tree.bipartition_tree_random`
    :type bipartition_tree_fn: Callable, optional

    :returns: New assignments for the nodes of ``graph``.
    :rtype: List[List[int]]
    """

    # frm: TODO: Refactoring:  Change the name of num_chunks_left to instead be
    #      num_districts_per_chunk.
    # frm: ???: It is not clear to me when num_chunks will not evenly divide num_dists.  In
    #           the only place where _get_seed_chunks() is called, it is inside an if-stmt
    #           branch that validates that num_chunks evenly divides num_dists...
    #
    num_chunks_left = num_dists // num_chunks

    # frm: TODO: Refactoring:  Change the name of parts below to be something / anything else.
    #      Normally parts refers to districts, but here is is just a way to keep track of
    #      sets of nodes for chunks.  Yes - they eventually become districts when this code gets
    #      to the base cases, but I found it confusing at this level...
    #
    parts = range(num_chunks)
    # frm: ???: I think that new_epsilon is the epsilon to use for each district, in which
    #           case the epsilon passed in would be for the  HERE...
    new_epsilon = epsilon / (num_chunks_left * num_chunks)
    if num_chunks_left == 1:
        new_epsilon = epsilon

    chunk_pop = 0
    for node in graph.node_indices:
        chunk_pop += graph.node_data(node)[pop_col]

    # frm: TODO: Refactoring:  See if there is a better way to structure this instead of a while
    # True loop...
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
        min_pop = pop_target * (1 - new_epsilon) * num_chunks_left
        max_pop = pop_target * (1 + new_epsilon) * num_chunks_left

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

        # Assign all nodes to one of the parts
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
        part_pop_as_dist = part_pop / num_chunks_left
        fake_epsilon = epsilon
        # frm: ???: If the chunk is for more than one district, divide epsilon by two
        if num_chunks_left != 1:
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
    """
    Helper function for _recursive_seed_part_inner. Returns the largest prime factor of ``n``
    less than ``ceil``, or None if all are greater than ceil.

    :param n: The number to find the largest prime factor for.
    :type n: int
    :param ceil: The upper limit for the largest prime factor.
    :type ceil: int

    :returns: The largest prime factor of ``n`` less than ``ceil``, or None if all are greater
        than ceil.
    :rtype: Optional[int]
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
    bipartition_tree_fn: Callable = partial(bipartition_tree, max_attempts=10000),
    node_repeats: int = 1,
    n: Optional[int] = None,
    ceil: Optional[int] = None,
) -> List[Set]:
    """
    Inner function for recursive_seed_part.

    Returns a list of sets of nodes with ``num_dists`` districts balanced within
    ``epsilon`` of ``pop_target``.

    This list of sets of nodes is conceptually equivalent to an Assignment object.
    Each set of nodes constitutes a district, but the district does not
    have an ID, and there is nothing that associates these nodes
    with a specific graph - that is implicit, depending on the graph
    object passed in, so the caller is responsible for knowing that
    the returned list of sets belongs to the graph passed in...

    It splits the graph into num_chunks chunks, and then recursively splits each chunk into
    ``num_dists``/num_chunks chunks.
    The number num_chunks of chunks is chosen based on ``n`` and ``ceil`` as follows:

    - If ``n`` is None, and ``ceil`` is None, num_chunks is the largest prime factor
      of ``num_dists``.
    - If ``n`` is None and ``ceil`` is an integer at least 2, then num_chunks is the
      largest prime factor of ``num_dists`` that is less than ``ceil``
    - If ``n`` is a positive integer, num_chunks equals n.

    Finally, if the number of chunks as chosen above does not divide ``num_dists``, then
    this function bites off a single district from the graph and recursively partitions
    the remaining graph into ``num_dists - 1`` districts.

    :param graph: The underlying graph structure.
    :type graph: Graph
    :param num_dists: number of districts to partition the graph into
    :type num_dists: int
    :param pop_target: Target population for each part of the partition
    :type pop_target: Union[float, int]
    :param pop_col: Node attribute key holding population data
    :type pop_col: str
    :param epsilon: How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
        of the partition can be
    :type epsilon: float
    :param bipartition_tree_fn: Function used to find balanced partitions at the 2-district level.
        Defaults to :func:`~gerrychain.tree.bipartition_tree`
    :type bipartition_tree_fn: Callable, optional
    :param node_repeats: Parameter for :func:`~gerrychain.tree.bipartition_tree` to use.
        Defaults to 1.
    :type node_repeats: int, optional
    :param n: Either a positive integer (greater than 1) or None. If n is a positive integer,
        this function will recursively create a seed plan by either biting off districts from
        graph or dividing graph into n chunks and recursing into each of these. If n is None,
        this function prime factors ``num_dists``=n_1*n_2*...*n_k (n_1 > n_2 > ... n_k) and
        recursively partitions graph into n_1 chunks. Defaults to None.
    :type n: Optional[int], optional
    :param ceil: Either a positive integer (at least 2) or None. Relevant only if n is None.
        If ``ceil`` is a positive integer then finds the largest factor of ``num_dists`` less
        than or equal to ``ceil``, and recursively splits graph into that number of chunks, or
        bites off a district if that number is 1. Defaults to None.
    :type ceil: Optional[int], optional

    :returns: New assignments for the nodes of ``graph``.
    :rtype: List of sets, each set is a district
    """

    """
    frm: TODO: Documentation: _recursive_seed_part_inner() - clarify what this does

    I started to update the documentation a while back, but didn't finish it.  I now
    need to remember what I was going to write, but the mere fact that I need to
    remember it is a good reason to write the documentation!



    This code is quite nice once you grok it.

    The goal is to find the given number of districts - but to do it in an
    efficient way - meaning with smaller graphs.  So conceptually, you want
    to...

    There are two base cases when the number of districts still to be found are
    either 1 or...


    Also - address this comment which I now do not grok:

        OK, but why is the logic above for num_chunks the correct number?  Is there
        a mathematical reason for it?  I assume so, but that explanation is missing...

        I presume that the reason is that something in the code that finds a
        district scales exponentially, so it makes sense to divide and conquer.
        Even so, why this particular strategy for divide and conquer?
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
            one_sided_cut=False,
        )

        # frm: TODO: Refactoring:  the name "one_sided_cut" seems unnecessarily opaque.
        #
        # First find out if it a term of art that means something to the GerryChain user
        # community.  I asked Google what it was, and Google said that it was not a term-of-art
        # for graph theory...
        #
        # In GerryChain "one_sided_cut" it means (if set to True) that the bipartition_tree()
        # algorithm should just carve off a single district from the nodes in the graph.  If
        # set to False it means the graph should be split into exactly two districts.
        #
        # There are two issues here: 1) I dislike the name and am inclined to change it, but
        # I am afraid that doing so will piss off legacy users - need Peter's input (but probably
        # not worth the risk of pissing someone off) and 2) whether for understandability it
        # would make sense to create a partial function that binds the value of "one_sided_cut"
        # just to provide a clearer name - something like: carve_out_one_district() .
        #
        # One more thing - I think it would be good practice to NEVER let one_sided_cut
        # default.  If only for documentation purposes, this parameter should always be explicitly
        # set and named, because carving off a district is very different from splitting
        # a graph into two districts.

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
        # frm: Create a list with the set of nodes returned by bipartition_tree_fn() and then recurse
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
    # frm: * TODO: Documentation: Add documentation for why a subgraph in call below
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


# frm TODO: Refactoring:   recursicve_seed_part() is never called - not in this file and not in any other
#     GerryChain file. Is it intended to be used by end-users?
#
# It calculates an initial assignment dictionary - for use in creating a Partition object.
#
# Are there other uses as well?  The comment for recursive_tree_part() implied that there
# might be other uses for creating an initial assigment-like dict...
#
# In January 2026, Peter said: I am unsure of what was in the mind of the creator of this
# function, but I have only ever seen it used for making initial partitions of a graph.
#
# He also said that it was OK to move stuff into other files:
#
# Moving recursive_seed_part, recursive_seed_part, and epsilon_tree_bipartition makes
# sense to me. My only organizational note is that I would like the recursive functions
# placed in something like "partition/initial_paritition_generators.py" rather than
# in "parition/partition.py" since they have been used for things outside of making
# a Partition object before, and we have some more algorithms that we might add to
# the mix later this year (also, I would like to try and move this repository to
# the "one thought per file" paradigm whenever we get the chance during this refactor).
# The epsilon_tree_bipartition is fine to go in "proposals/tree_proposals.py", however.
#
# And: Note to self: we will need to make sure to add this to the top of the release notes..
#


def recursive_seed_part(
    graph: Graph,
    parts: Sequence,
    pop_target: Union[float, int],
    pop_col: str,
    epsilon: float,
    bipartition_tree_fn: Callable = partial(bipartition_tree, max_attempts=10000),
    node_repeats: int = 1,
    n: Optional[int] = None,
    ceil: Optional[int] = None,
) -> Dict:
    """
    Returns an assignment dictionary with ``num_dists`` districts balanced within ``epsilon`` of
    ``pop_target`` by recursively splitting graph using _recursive_seed_part_inner.

    :param graph: The graph
    :type graph: Graph
    :param parts: Iterable of part labels (like ``[0,1,2]`` or ``range(4)``
    :type parts: Sequence
    :param pop_target: Target population for each part of the partition
    :type pop_target: Union[float, int]
    :param pop_col: Node attribute key holding population data
    :type pop_col: str
    :param epsilon: How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
        of the partition can be
    :type epsilon: float
    :param bipartition_tree_fn: Function used to find balanced partitions at the 2-district level
        Defaults to :func:`~gerrychain.tree.bipartition_tree`
    :type bipartition_tree_fn: Callable, optional
    :param node_repeats: Parameter for :func:`~gerrychain.tree.bipartition_tree` to use.
        Defaults to 1.
    :type node_repeats: int, optional
    :param n: Either a positive integer (greater than 1) or None. If n is a positive integer,
        this function will recursively create a seed plan by either biting off districts from graph
        or dividing graph into n chunks and recursing into each of these. If n is None, this
        function prime factors ``num_dists``=n_1*n_2*...*n_k (n_1 > n_2 > ... n_k) and recursively
        partitions graph into n_1 chunks. Defaults to None.
    :type n: Optional[int], optional
    :param ceil: Either a positive integer (at least 2) or None. Relevant only if n is None. If
        ``ceil`` is a positive integer then finds the largest factor of ``num_dists`` less than or
        equal to ``ceil``, and recursively splits graph into that number of chunks, or bites off a
        district if that number is 1. Defaults to None.
    :type ceil: Optional[int], optional

    :returns: New assignments for the nodes of ``graph``.
    :rtype: dict
    """

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
