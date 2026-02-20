import random
from typing import (
    Callable,
    Dict,
    Optional,
)

# frm:  import the new Graph object which encapsulates NX and RX Graph...
from ..graph import Graph

# frm: TODO: Documentation: Update the high level description for spanning_tree.py below

"""
This module provides tools and algorithms for manipulating and analyzing graphs,
particularly focused on partitioning graphs based on population data. It leverages the
GerryChain Graph object to handle graph structures and implements various algorithms for graph
partitioning and tree traversal.

Key functionalities include:

- Implementation of random and uniform spanning trees for graph partitioning.
- The `_PopulatedGraph` class, which represents a graph with additional population data,
  and methods for assessing and modifying this data.
- Functions for finding balanced edge cuts in a populated graph, either through
  contraction or memoization techniques.
- A suite of functions (`bipartition_tree`, `recursive_tree_part`, `_get_seed_chunks`, etc.)
  for partitioning graphs into balanced subsets based on population targets and tolerances.
- Utility functions like `get_max_prime_factor_less_than` and `_recursive_seed_part_inner`
  to assist in complex partitioning tasks.

Dependencies:

- random: Provides random number generation for probabilistic approaches.
- typing: Used for type hints.

Last Updated: January 2026

RustworkX Issues:

Note: This module has been modified in order to be able to operate on
RustworkX.PyGraph objects in addition to NetworkX.Graph objects.  The
new GerryChain Graph object embeds a graph object that can be based
either on NetworkX or RustworkX (the old GerryChain graph object was
a subclass of NetworkX.Graph).  The reason for supporting
RustworkX.PyGrapy is performance - it is much faster than NetworkX.

The default usage model is for users to create graphs using Networkx,
both because of legacy concerns but also because it is just convenient
to create graphs in NetworkX.  When the user creates a Partition
object, the embedded NetworkX.Graph object will be automatically
converted to be a RustworkX.PyGraph object.  And since most of the
routines in this module are used after the creation of a Partition
object, the underlying graph operations will be performed by
RustworkX code.

There is a way to override this behavior by setting the value of a
variable in the code (in partition.py).  The variable in
partition.py that controls this (and its default setting) is:

    test_performance_using_NX_graph = False

Many of the functions in this file operate on subgraphs which
behave differently from NX subgraphs.  In particular, RustworkX subgraphs
typically change the IDs for the nodes in the subgraph, so that a node with
an ID of say, 5, in a parent graph might have an ID of say, 2, in the subgraph.
It is the same node, with the same data, but its ID has changed.

To deal with subgraphs having different node_ids from their parent graph
the code has implemented mappings (dictionaries) for subgraph node_ids to
parent graph node_ids, allowing routines to convert any results obtained
using a subgraph to the appropriate node_ids for the parent graph.  Note
that the same issue applies for edges - they need to be converted back to
use the node_ids of the parent graph.

To manage the need to translate node_ids from subgraphs to parent graphs,
the code only calls subgraph as an actual parameter to a function call.
This prevents subgraph node_ids from being available (and hence causing bugs)
in the context of the calling code.  Functions that return node_ids or
edge_ids or edges have the obligation to translate the node_ids of
the subgraph back into the appropriate node_ids for the parent graph.

So - if you decide to write custom code that involves subgraphs, please
spend a little time reviewing how the code in this module is implemented
so that you can avoid subtle nasty bugs...

Note: Predecessor and successor functions have been moved to the new
GerryChain Graph object.  The reason for moving them was to remove dependencies
on NetworkX (and RustworkX) from this module.
"""

"""
frm: TODO: Get OK from Peter for proposed changes (to be made in near future):

I have started the refactoring of this module, but there is much that I would
like to do.  Before I do it, however, I would like to get your feedback.

I am pressed for time - want to get this PR done for tomorrow, so this will
be a little scattershot, but hopefully it is better to have it mostly in one
place.  If it is too confusing, then let me know and I will spend some time
to make it clearer and then post a new PR (or an updated one).

The first thing I would like to do is to move some functions out of this
module so that it can concentrate on biparition_tree() and the code that
supports it.

Peter said (January 2026): Fine with me! We can make "tree" into it's
own submodule and put each distinct kind of thing in its own file.

Move recursive_tree_part() and recursive_seed_part()

    Maybe to assignment.py or partition.py because these routines are used to create
    assignments.  They use tree functions but they are not themselves tree functions.

Move espilon_tree_bipartition() tree_proposals.py

    This routine, epsilon_tree_biparition() is only ever used by recom(), and it
    will probably end up only being used by recom().  So that is one reason for
    moving it - so that it will be closer to its use.

    However, as with the argument for moving recursive_tree_part() and recursive_seed_part()
    out of tree.py, epsilon_tree_bipartition() is not a general purpose tree operation, and
    moving it out of tree.py will reduce the cognitive load for someone trying to
    understand what tree.py is all about.

Unify the code that does the heavy lifting for biparition_tree().

    This module is hard to grok, and putting all of the code that uses function
    variables and region_surcharges, and one_sided_cuts into fewer places
    simplifies the logic.

    I created a routine _get_possible_cuts_and_populated_graph() which does the
    heavy lifting, and then had other routines call it.  Take a look and see if
    it looks good as-is or whether you would like tweaks or wholesale different
    approach.

    It is unfortunate that this routine returns a tuple.  It had to do so because
    region_surchage logic needed access to the populated graph so that it could
    do its fancy weighted cut. On the other hand, it is an internal function, so
    the ugliness is internal...

    I would like to unify the signatures of random_spanning_tree() and
    uniform_spanning_tree() - just to get rid of the tests against the signatures
    of functions.  This is perhaps religion - the code works just fine as-is,
    but OTOH there seems little harm in unifying them.

    Peter said (January 2026): I would actually prefer a more unified
    interface. It makes it way easier to maintain when things are consistent.

    There are some other questions in the comments below about why we even
    offer uniform_spanning_tree() - I would be interested in your answers to
    those questions.

    Peter said (January 2026): The broad answer is that uniform spanning
    trees samples from a completely different probability space compared to
    minimum spanning trees and there are reasons for preferring one
    distribution or the other.

    There are tons of comments that you are welcome to ignore.  As I said, I have
    lots of thoughts about how to improve this code, but the above are the
    biggies.

    All of the tests pass now, so I think this is solid.

    Looking forward to your feedback!

    -Fred



"""

# frm: TODO: Refactoring:  random_spanning_tree() and uniform_spanning_tree() should have same signature
#
# These two functions are essentially instances of a generic spanning_tree_fn that is used as a
# function parameter.  Because these two routines have different signatures in the current
# codebase, the routines that take a spanning_tree_fn parameter need to inspect the actual
# parameter's signature to see what to do, which is kind of exactly what a generic should NOT be.
#
# So, I suggest that we modify the signatures of these two functions so that they have the
# same signature, which would be:
#
#     <fname>(
#       graph: Graph,
#       choice: Callable = random.choice,
#       region_surcharge: dict = {}
#     )
#
# The uniform_spanning_tree() function could just ignore the "region_surcharge" parameter -
# or maybe issue a warning if that parameter were not an empty dict.  Similarly, the
# random_spanning_tree() function could just ignore the "choice" parameter - or maybe
# issue a warning it it were anything other than random.choice.
#
# Ask Peter if he agrees.


def random_spanning_tree(graph: Graph, region_surcharge: Optional[Dict] = None) -> Graph:
    """
    Builds a spanning tree chosen by Kruskal's method using random weights.

    The region_surcharge parameter allows the caller to bias the selection of
    edges by increasing the weights of some edges that the caller would like
    to be kept together (if possible).

    Kruskal's method chooses the edges with the lowest weight first, so edges
    with high weights will be selected last - with the highest weights not chosen
    at all (once all the nodes are in the tree, the algorithm stops adding edges).
    This has the effect of making adjacent nodes that belong to the same region be
    highly connected.

    Note that the algorihm adds weights to edges when the nodes are NOT in the
    same region.  So, in the case where we have a region_surcharge adding an
    additional weight of 1 to all edges where the two nodes are NOT in the
    same municipality, the weights of edges for nodes in the same municipality
    will be less than 1 while the weights of all other edges will be greater
    than one, which would guarantee that all of the nodes in a given municipality
    would be connected to each other.  This would not guarantee that all
    of the nodes in a municipality were placed in the same district, but it
    would certainly prioritize preserving municipalities in a few rather than
    a large number of different districts.

    If no region_surcharges are provided, then the algorithm just randomly
    specifies the weights of all edges before generating an MST which is
    essentially a random spanning_tree generator.  In this case, the caller
    could have instead used the uniform_spanning_tree() function.  The performance
    difference between uniform_spanning_tree() and random_spanning_tree()
    depends on the structure of the graph.

    In short, if you want to bias the selection of districts to keep some nodes
    together, you want to use this routine, random_spanning_tree().

    Note that the random weights applied to edges have values between 0 and 1
    so the additional weights supplied in the region_surcharge should be sized
    appropriately.  If the region_surcharge weight is greater than 1, then it
    will be heavier than any other edge that has not had a surcharge applied to
    it.

    :param graph: The input graph to build the spanning tree from.
    :type graph: Graph
    :param region_surcharge: Dictionary of surcharges to add to the random
        weights used in region-aware variants.
    :type region_surcharge: Optional[Dict], optional

    :returns: The maximal spanning tree represented as a GerryChain Graph.
    :rtype: Graph
    """

    """
    frm: RX Documentation:

    As far as I can tell a spanning tree is only ever used to populate a _PopulatedGraph
    and so, there is no need to worry about translating the spanning tree's nodes into
    the context of the parent.  Stated differently, a spanning tree is not used to
    compute something about a subgraph but rather to compute something about whatever
    graph is currently being dealt with.

    In short, I am assuming that we can ignore the fact that RX subgraphs have different
    node_ids for this function and all will be well...
    """

    # frm: TODO: Refactoring: What is up with region_surcharge being unset?  The region_surcharge
    #               is only ever accessed in this routine in the for-loop below to
    #               increase the weight on the edge - setting it to be an empty dict
    #               just prevents the code below from blowing up.  Why not just put
    #               a test for the surcharge for-loop alone:
    #
    #                    if not region_surcharge is None:
    #                        for key, value in region_surcharge.items():
    #                            ...
    #
    # Peter's comments from PR:
    #
    # peterrrock2 last week
    # This is one of mine. I added the region surcharge stuff in an afternoon,
    # so I probably did this to prevent the more than 3 levels of indentation
    # and to make the reasoning easier to track as I was adding the feature.
    #
    # Collaborator
    # Author
    # @peterrrock2 peterrrock2 last week
    # Also, I imagine that I originally wanted the function modification to look like
    #
    #    def random_spanning_tree(
    #         graph: Graph,
    #         region_surcharge: dict = dict()
    #     ) -> Graph:
    #
    # but doing this sort of thing is generally a bad idea in python since the
    # dict() is instantiated at import time and then all future calls to the
    # function reference the same dict when the surcharge is unset. Not a problem
    # for this function, but the accepted best-practice is to change the above to
    #
    #     def random_spanning_tree(
    #         graph: Graph,
    #         region_surcharge: Optional[Dict] = None
    #     ) -> Graph:
    #         if region_surcharge is None:
    #             region_surcharge = dict()
    #
    # since this doesn't reuse the reference.

    if region_surcharge is None:
        region_surcharge = dict()

    # Add a random weight to each edge in the graph with the goal of
    # causing the selection of a different (random) spanning tree based
    # on those weights.  Note that the value of this random weight
    # will be between 0 and 1.
    #
    # If a region_surcharge was passed in, then add the
    # appropriate region_surcharge value to the weight for those
    # edges that are NOT in the region.
    #
    for edge_id in graph.edge_indices:
        edge = graph.get_edge_from_edge_id(edge_id)
        weight = random.random()

        # If there are any entries in the region_surcharge dict, then add
        # additional weight to the edge if the nodes in the edge are not
        # in the same "region", that is:
        #
        #    * if one of the nodes is NOT in a region (for instance in the
        #      case of a "municipality" region defined by the key "muni",
        #      the node was not in any municpality and hence there was no
        #      node_data for the atrribute, "muni")
        #
        #    * or if the nodes were in different "regions"
        #
        for key, value in region_surcharge.items():
            # We surcharge edges that are in different regions and those that are not in any region
            node_id1 = edge[0]
            node_id2 = edge[1]
            node_id1_region = graph.node_data(node_id1)[key]
            node_id2_region = graph.node_data(node_id2)[key]
            if (
                node_id1_region != node_id2_region
                or node_id1_region is None
                or node_id2_region is None
            ):
                weight += value

        graph.edge_data(edge_id)["random_weight"] = weight

    graph.verify_graph_is_valid()

    # frm: TODO: Documentation:  Think a bit about original_nx_node_ids
    #
    # Original node_ids refer to the node_ids used when a graph was created.
    # This mostly means remembering the NX node_ids when you create an RX
    # based Graph object.  In the code below, we create an RX based Graph
    # object, but we do not do anything to map original node_ids.  This is
    # probably OK, but it depends on how the spanning tree is used elsewhere.
    #
    # In short, worth some thought...

    # frm: TODO: Refactoring: Code: Eliminate NX dependence in tree.py
    #
    # Create a routine in graph.py to compute a minimum spanning tree
    # and then use that routine here.
    #
    # The fact that the NX version uses edge data directly while the RX
    # version uses a function (that does the same thing) means that
    # a utility routine in graph.py that did the delegation to NX or RX
    # would need to have different parameters - a string vs. a function.
    # So, maybe this is not worth doing after all...
    #
    # Note that the RX version is *much* faster

    minimum_spanning_tree = graph.minimum_spanning_tree_from_edge_weight(
        edge_weight_attribute_name="random_weight"
    )
    return minimum_spanning_tree


def uniform_spanning_tree(graph: Graph, choice: Callable = random.choice) -> Graph:
    """
    Builds a spanning tree chosen uniformly from the space of all
    spanning trees of the graph. Uses Wilson's algorithm.

    If interested, there is a nice animated description of Wilson's
    algorithm here:

    https://weblog.jamisbuck.org/2011/1/20/maze-generation-wilson-s-algorithm

    A brief description of Wilson's Alorithm follows:

    Pick a node at random for the root node of the spanning tree.  Then
    pick any other node and do a random walk until you end up at the root
    node, but as you go remember the last move you made at each node - which
    will overwrite any previous move.  When you end up at the root node, go
    back to the starting node and follow the path left behind, which will
    cleverly contain no cycles because the paths for any cycles were
    overwritten.

    Add the nodes in the path (remembering child and parent) to the list
    of nodes you have added to the tree.  Then pick another node at random
    that is not already in the tree and do another random walk, ending
    when you fall on a node already in the tree.  Then add the nodes for
    that random walk to the tree.

    Rinse and repeat until all nodes have been added to the tree.

    :param graph: Graph
    :type graph: Graph
    :param choice: :func:`random.choice`. Defaults to :func:`random.choice`.
    :type choice: Callable, optional

    :returns: A spanning tree of the graph chosen uniformly at random.
    :rtype: Graph
    """

    # Pick a starting point at random
    root_id = choice(list(graph.node_indices))

    # Initiallize the tree to contain the root_node (with no parent)
    tree_nodes = set([root_id])
    parent_node_id = {root_id: None}

    for node_id in graph.node_indices:

        # Random walk (perhaps with cycles) that records the
        # last path taken before hitting a node already in
        # tree_nodes.  Note that recording the last path
        # taken effectively removes cycles from the path.
        u = node_id
        while u not in tree_nodes:
            parent_node_id[u] = choice(list(graph.neighbors(u)))
            u = parent_node_id[u]

        # Record the "direct" path (the one with no cycles)
        # from the starting node, u, to a node already
        # in tree_nodes.
        u = node_id
        while u not in tree_nodes:
            tree_nodes.add(u)
            u = parent_node_id[u]

    G = Graph.from_null_networkx()

    for node_id in tree_nodes:
        if parent_node_id[node_id] is not None:
            G.add_edge(node_id, parent_node_id[node_id])

    return G
