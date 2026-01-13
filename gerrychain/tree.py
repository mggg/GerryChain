import itertools
import random
import warnings
from collections import deque, namedtuple
from functools import partial
from inspect import signature
from typing import (  # Hashable,; Tuple,
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
from .graph import Graph

"""
This module provides tools and algorithms for manipulating and analyzing graphs,
particularly focused on partitioning graphs based on population data. It leverages the
GerryChain Graph object to handle graph structures and implements various algorithms for graph
partitioning and tree traversal.

Key functionalities include:

- Implementation of random and uniform spanning trees for graph partitioning.
- The `PopulatedGraph` class, which represents a graph with additional population data,
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

    There are some other questions in the comments below about why we even
    offer uniform_spanning_tree() - I would be interested in your answers to
    those questions.

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

    As far as I can tell a spanning tree is only ever used to populate a PopulatedGraph
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


# frm TODO: Documentation: PopulatedGraph
#
# State what the purpose of this class is in the docstring comment below.
#
# It is only ever used inside this module (except) for testing.  If that is so, then
# change the name to have a leading underscore.
#
class PopulatedGraph:
    """
    A class representing a graph with population information.

    :ivar graph: The underlying graph structure.
    :type graph: Graph
    :ivar subsets: A dictionary mapping nodes to their subsets.
    :type subsets: Dict
    :ivar population: A dictionary mapping nodes to their populations.
    :type population: Dict
    :ivar tot_pop: The total population of the graph.
    :type tot_pop: Union[int, float]
    :ivar ideal_pop: The ideal population for each district.
    :type ideal_pop: float
    :ivar epsilon: The tolerance for population deviation from the ideal population within each
        district.
    :type epsilon: float
    """

    def __init__(
        self,
        graph: Graph,
        populations: Dict,
        ideal_pop: Union[float, int],
        epsilon: float,
    ) -> None:
        """
        :param graph: The underlying graph structure.
        :type graph: Graph
        :param populations: A dictionary mapping nodes to their populations.
        :type populations: Dict
        :param ideal_pop: The ideal population for each district.
        :type ideal_pop: Union[float, int]
        :param epsilon: The tolerance for population deviation as a percentage of
            the ideal population within each district.
        :type epsilon: float
        """
        self.graph = graph
        self.subsets = {node_id: {node_id} for node_id in graph.node_indices}
        self.population = populations.copy()
        self.tot_pop = sum(self.population.values())
        self.ideal_pop = ideal_pop
        self.epsilon = epsilon
        self._degrees = {node_id: graph.degree(node_id) for node_id in graph.node_indices}

        # frm: TODO: Refactor: _degrees ???  Why separately store the degree of every node?
        #
        # The _degrees data member above is used to define a method below called "degree()"
        # What is odd is that the implementation of this degree() method could just as
        # easily have been self.graph.degree(node_id).  And in fact, every call on the
        # new degree function could be replaced with just <PopulatedGraph>.graph.degree(node_id)
        #
        # So unless there is a big performace gain (or some other reason), I would be
        # in favor of deleting the degree() method below and just using
        # <PopulatedGraph>.graph.degree(node_id) on the assumption that both NX and RX
        # have an efficient implementation of degree()...

    def __iter__(self):
        # Note: in the pre RustworkX code, this was implemented as:
        #
        #     return iter(self.graph)
        #
        # But RustworkX does not support __iter__() - it is not iterable.
        #
        # The way to do this in the new RustworkX based code is to use
        # the node_indices() method which is accessed as a property as in:
        #
        #     for node_id in graph.node_indices:
        #         ...do something with the node_id
        #
        raise NotImplementedError("Graph is not iterable - use graph.node_indices instead")

    def degree(self, node) -> int:
        return self._degrees[node]

    def contract_node(self, node, parent) -> None:
        self.population[parent] += self.population[node]
        self.subsets[parent] |= self.subsets[node]
        self._degrees[parent] -= 1

    # frm: only ever used inside this file
    #       But maybe this is intended to be used externally...
    def has_ideal_population(self, node, one_sided_cut: bool = False) -> bool:
        """
        Checks if a node has an ideal population within the graph up to epsilon.

        :param node: The node to check.
        :type node: Any
        :param one_sided_cut: Whether or not we are cutting off a single district. When
            set to False, we check if the node we are cutting and the remaining graph
            are both within epsilon of the ideal population. When set to True, we only
            check if the node we are cutting is within epsilon of the ideal population.
            Defaults to False.
        :type one_sided_cut: bool, optional

        :returns: True if the node has an ideal population within the graph up to epsilon.
        :rtype: bool
        """

        # frm: TODO: Refactoring: Create a helper function for this
        #
        # This logic is repeated several times in this file.  Consider
        # refactoring the code so that the logic lives in exactly
        # one place.
        #
        # When thinking about refactoring, consider whether it makes
        # sense to toggle what this routine does by the "one_sided_cut"
        # parameter.  Why not have two separate routines with
        # similar but distinguishing names.  I need to be absolutely
        # clear about what the two cases are all about, but my current
        # hypothesis is that when one_sided_cut == False, we are looking
        # for the edge which when cut produces two districts of
        # approximately equal size - so a bisect rather than a find all
        # meaning...

        if one_sided_cut:
            return abs(self.population[node] - self.ideal_pop) < self.epsilon * self.ideal_pop

        return (
            abs(self.population[node] - self.ideal_pop) <= self.epsilon * self.ideal_pop
            and abs((self.tot_pop - self.population[node]) - self.ideal_pop)
            <= self.epsilon * self.ideal_pop
        )

    def __repr__(self) -> str:
        graph_info = f"Graph(nodes={len(self.graph.node_indices)}, edges={len(self.graph.edges)})"
        return (
            f"{self.__class__.__name__}("
            f"graph={graph_info}, "
            f"total_population={self.tot_pop}, "
            f"ideal_population={self.ideal_pop}, "
            f"epsilon={self.epsilon})"
        )


# frm: ???: Is a Cut used anywhere outside this file?

# Definition of Cut namedtuple
# Tuple that is used in the find_balanced_edge_cuts function
Cut = namedtuple("Cut", "edge weight subset")
Cut.__new__.__defaults__ = (None, None, None)
Cut.__doc__ = "Represents a cut in a graph."
Cut.edge.__doc__ = "The edge where the cut is made. Defaults to None."
Cut.weight.__doc__ = "The weight assigned to the edge (if any). Defaults to None."
Cut.subset.__doc__ = "The (frozen) subset of nodes on one side of the cut. Defaults to None."

# frm: TODO:  Documentation:  Document what Cut objects are used for
#
# Not sure how this is used, and so I do not know whether it needs
#               to translate node_ids to the parent_node_id context.  I am assuming not...
#
# Here is an example of how it is used (in test_tree.py):
#
#        method=partial(
#            bipartition_tree,
#            max_attempts=10000,
#            balance_edge_fn=find_balanced_edge_cuts_contraction,
#
# and another in the same test file:
#
#    populated_tree = PopulatedGraph(
#        tree, {node: 1 for node in tree}, len(tree) / 2, 0.5
#    )
#    cuts = find_balanced_edge_cuts_contraction(populated_tree)

# frm: TODO: Refactoring: params are balance_edge_fn but routines are balanced_edge_...
#
# Another nit, but it would be nice if the parameter names were balanced_edge_fn (with a 'd'),
# but that is probably not possible given legacy code.
#
# Ask Peter to confirm that we should not change the name of either the param or the functions...


def find_balanced_edge_cuts_contraction(
    h: PopulatedGraph, one_sided_cut: bool = False, choice: Callable = random.choice
) -> List[Cut]:
    """
    Find balanced edge cuts using contraction.

    :param h: The populated graph.
    :type h: PopulatedGraph
    :param one_sided_cut: Whether or not we are cutting off a single district. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param choice: The function used to make random choices.
    :type choice: Callable, optional

    :returns: A list of balanced edge cuts.
    :rtype: List[Cut]
    """

    root = choice([node_id for node_id in h.graph.node_indices if h.degree(node_id) > 1])
    # BFS predecessors for iteratively contracting leaves
    pred = h.graph.predecessors(root)

    cuts = []

    # frm:  Work up from leaf nodes to find subtrees with the "correct"
    #       population.  The algorighm starts with real leaf nodes, but
    #       if a node does not have the "correct" population, then that
    #       node is merged (contracted) into its parent, effectively
    #       creating another leaf node which is then added to the end
    #       of the queue.
    #
    #       In this way, we calculate the total population of subtrees
    #       by going bottom up, until we find a subtree that has the
    #       "correct" population for a cut.

    # frm: ??? Note that there is at least one other routine in this file
    #           that does something similar (perhaps exactly the same).
    #           Need to figure out why there are more than one way to do this...

    leaves = deque(node_id for node_id in h.graph.node_indices if h.degree(node_id) == 1)
    while len(leaves) > 0:
        leaf = leaves.popleft()
        if h.has_ideal_population(leaf, one_sided_cut=one_sided_cut):
            # frm: If the population of the subtree rooted in this node is the correct
            #       size, then add it to the cut list.  Note that if one_sided_cut == False,
            #       then the cut means the cut bisects the partition (frm: ??? need to verify
            #       this).
            e = (leaf, pred[leaf])
            cuts.append(
                Cut(
                    edge=e,
                    weight=h.graph.edge_data(h.graph.get_edge_id_from_edge(e)).get(
                        "random_weight", random.random()
                    ),
                    subset=frozenset(h.subsets[leaf].copy()),
                )
            )
        # Contract the leaf:  frm: merge the leaf's population into the parent and add the
        # parent to "leaves"
        parent = pred[leaf]
        # frm: Add child population and subsets to parent, reduce parent's degree by 1
        #       This effectively removes the leaf from the tree, adding all of its data
        #       to the parent.
        h.contract_node(leaf, parent)
        if h.degree(parent) == 1 and parent != root:
            # frm: Only add the parent to the end of the queue when we are merging
            #       the last leaf - this makes sure we only add the parent node to
            #       the queue one time...
            leaves.append(parent)
    return cuts


def _calc_pops(succ, root, h):
    """
    Calculates the population of each subtree in the graph
    by traversing the graph using a depth-first search.

    :param succ: The successors of the graph.
    :type succ: Dict
    :param root: The root node of the graph.
    :type root: Any
    :param h: The populated graph.
    :type h: PopulatedGraph

    :returns: A dictionary mapping nodes to their subtree populations.
    :rtype: Dict
    """
    # frm:  This took me a while to sort out what was going on.
    # Conceptually it is easy - given a tree anchored in a root node,
    # calculate the population in each subtree going bottom-up.
    # The stack (deque) provides the mechanism for going bottom-up.
    # On the way down, you just put nodes in the stack (append is like
    # push() which seems odd to me, but whatever...) then on the way back
    # up, you add the totals for each child to your own population and
    # presto you have the total population for each subtree...
    #
    # For this to work, you just need to have a list of nodes with
    # their successors associated with them...
    #
    subtree_pops: Dict[Any, Union[int, float]] = {}
    stack = deque(n for n in succ[root])
    while stack:
        next_node = stack.pop()
        if next_node not in subtree_pops:
            if next_node in succ:
                children = succ[next_node]
                if all(c in subtree_pops for c in children):
                    subtree_pops[next_node] = sum(subtree_pops[c] for c in children)
                    subtree_pops[next_node] += h.population[next_node]
                else:
                    stack.append(next_node)
                    for c in children:
                        if c not in subtree_pops:
                            stack.append(c)
            else:
                subtree_pops[next_node] = h.population[next_node]

    return subtree_pops


# frm: Only used in one function and only in this module...
def _part_nodes(start, succ):
    """
    Partitions the nodes of a graph into two sets.
    based on the start node and the successors of the graph.

    :param start: The start node.
    :type start: Any
    :param succ: The successors of the graph.
    :type succ: Dict

    :returns: A set of nodes for a particular district (only one side of the cut).
    :rtype: Set
    """

    """
    frm: Compute the nodes in a subtree defined by a Cut.

    This routine computes the set of nodes in a subtree rooted in the
    node identified by "start" in the tree defined by "succ".

    As such it is highly dependent on context and is not generally
    useful.  That is, it is essentially just a way to refactor some
    code used in a couple of places so that the logic in the code is
    in one place instead of several.

    To be specific, Cuts are always relative to a specific tree for
    a partition.  This tree is a "spanning tree" that converts the
    graph into a DAG.  Cuts are then computed by finding subtrees
    of that DAG that have the appropriate population (this could
    presumably be modified to include other factors).

    When a Cut is created, we want to collect all of the nodes that
    are in the subtree, and this is what this routine does.  It
    merely starts at the root of the subtree (start) and goes down
    the subtree, adding each node to a set.

    frm: TODO:  Documentation: Rename this to be more descriptive - perhaps ]
                     something like: _nodes_in_subtree() or
                     _nodes_for_cut()

    frm: TODO:  Documentation: Add the above explanation for what a Cut is and how
                we find them by converting the graph to a DAG and
                then looking for subtrees to a block header at the
                top of this file.  It will give the reader some
                idea wtf is going on...  ;-)
    """
    nodes = set()
    queue = deque([start])
    while queue:
        next_node = queue.pop()
        if next_node not in nodes:
            nodes.add(next_node)
            if next_node in succ:
                for c in succ[next_node]:
                    if c not in nodes:
                        queue.append(c)
    return nodes


# frm: used externally by tree_proposals.py
def find_balanced_edge_cuts_memoization(
    h: PopulatedGraph, one_sided_cut: bool = False, choice: Callable = random.choice
) -> List[Cut]:
    """
    Find balanced edge cuts using memoization.

    This function takes a PopulatedGraph object and a choice function as input and returns a list
    of balanced edge cuts. A balanced edge cut is defined as a cut that divides the graph into
    two subsets, such that the population of each subset is close to the ideal population
    defined by the PopulatedGraph object.

    :param h: The PopulatedGraph object representing the graph.
    :type h: PopulatedGraph
    :param one_sided_cut: Whether or not we are cutting off a single district. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param choice: The choice function used to select the root node.
    :type choice: Callable, optional

    :returns: A list of balanced edge cuts.
    :rtype: List[Cut]
    """

    """
    frm: ???: confused...

    This function seems to be used for two very different purposes, depending on the
    value of the parameter, one_sided_cut.  When true, the code looks for lots of cuts
    that would create a district with the right population - both above and below the
    node being considered.  Given that it is operating on a tree, one would assume that
    there is only one (or perhaps two if one node's population was tiny) cut for the top
    of the tree, but there should be many for the bottom of the tree.

    However, if the paramter is set to false (the default), then the code checks to see
    whether a cut would produce two districts - on above and one below the tree that
    have the right populations.  In this case, the code is presumatly looking for the
    single node (again there might be two if one node's population was way below epsilon)
    that would bisect the graph into two districts with a tolerable population.

    If I am correct, then there is an opportunity to clarify these two uses - perhaps
    with wrapper functions.  I am also a bit surprised that snippets of code are repeated.
    Again - this causes mental load for the reader, and it is an opportunity for bugs to
    creep in later (you fix it in one place but not the other).  Not sure this "clarification"
    is desired, but it is worth considering...
    """

    # frm: ???:  Why does a root have to have degree > 1?  I would think that any node would do...

    root = choice([node_id for node_id in h.graph.node_indices if h.degree(node_id) > 1])
    pred = h.graph.predecessors(root)
    succ = h.graph.successors(root)
    total_pop = h.tot_pop

    # Calculate the population of each subtree in the "succ" tree
    subtree_pops = _calc_pops(succ, root, h)

    cuts = []

    if one_sided_cut:
        for node, tree_pop in subtree_pops.items():
            if abs(tree_pop - h.ideal_pop) <= h.ideal_pop * h.epsilon:
                # frm: If the subtree for this node has a population within epsilon
                #       of the ideal, then add it to the cuts list.
                e = (node, pred[node])  # get the edge from the parent to this node
                wt = random.random()
                # frm: Add the cut - set its weight if it does not already have one
                #       and remember all of the nodes in the subtree in the frozenset
                cuts.append(
                    Cut(
                        edge=e,
                        weight=h.graph.edge_data(h.graph.get_edge_id_from_edge(e)).get(
                            "random_weight", wt
                        ),
                        subset=frozenset(_part_nodes(node, succ)),
                    )
                )
            elif abs((total_pop - tree_pop) - h.ideal_pop) <= h.ideal_pop * h.epsilon:
                # frm: If the population of everything ABOVE this node in the tree is
                #       within epsilon of the ideal, then add it to the cut list too.
                e = (node, pred[node])
                wt = random.random()
                cuts.append(
                    Cut(
                        edge=e,
                        weight=h.graph.edge_data(h.graph.get_edge_id_from_edge(e)).get(
                            "random_weight", wt
                        ),
                        subset=frozenset(set(h.graph.node_indices) - _part_nodes(node, succ)),
                    )
                )

        return cuts

    # frm: TODO: Refactoring: Change this code to make its two use cases clearer:
    #
    # One use case is bisecting the graph (one_sided_cut is False).  The
    # other use case is to peel off one part (district) with the appropriate
    # population.
    #
    # Not quite clear yet exactly how to do this, but a return stmt in the middle
    # of the routine (above) is a clear sign that something is odd.  Perhaps
    # we keep the existing function signature but immediately split the code
    # into calls on two separate routines - one for each use case.

    # We are looking for a way to bisect the graph (one_sided_cut is False)
    for node, tree_pop in subtree_pops.items():

        # frm: TODO: Refactoring:  Why keep looping if you have found a solution?
        #
        # This is perhaps a nit, but it is technically possible to have more than one
        # edge that, if cut, would result in two almost equal sized districts.  One example
        # is a root node that itself has zero population and two child nodes each of which
        # has in its subtree half of the population.  In this case cutting either of the
        # edges to the root's children would work - hence more than one solution.
        #
        # However, I do not think that any code in GerryChain cares about this in the
        # case when it wants two equal sized districts from one graph.  So, we could
        # be a little more efficient by just returning after finding the first (and
        # probably the only) solution.
        #
        # Ask Peter what he thinks...

        if (abs(tree_pop - h.ideal_pop) <= h.ideal_pop * h.epsilon) and (
            abs((total_pop - tree_pop) - h.ideal_pop) <= h.ideal_pop * h.epsilon
        ):
            e = (node, pred[node])
            wt = random.random()
            # frm: TODO: Performance: Think if code below can be made faster...
            cuts.append(
                Cut(
                    edge=e,
                    weight=h.graph.edge_data(h.graph.get_edge_id_from_edge(e)).get(
                        "random_weight", wt
                    ),
                    subset=frozenset(set(h.graph.node_indices) - _part_nodes(node, succ)),
                )
            )
    return cuts


# frm: only used in this file and in a test
class BipartitionWarning(UserWarning):
    """
    Generally raised when it is proving difficult to find a balanced cut.
    """

    pass


# frm: only used in this file and in a test
class ReselectException(Exception):
    """
    Raised when the tree-splitting algorithm is unable to find a
    balanced cut after some maximum number of attempts, but the
    user has allowed the algorithm to reselect the pair of
    districts from parent graph to try and recombine.
    """

    pass


def _max_weight_choice(cut_edge_list: List[Cut]) -> Cut:
    """
    Each Cut object in the list is assigned a random weight.
    This random weight is either assigned during the call to
    the minimum spanning tree algorithm (Kruskal's) algorithm
    or it is generated during the selection of the balanced edges
    (cf. :meth:`find_balanced_edge_cuts_memoization` and
    :meth:`find_balanced_edge_cuts_contraction`).
    This function returns the cut with the highest weight.

    In the case where a region aware chain is run, this will
    preferentially select for cuts that span different regions, rather
    than cuts that are interior to that region (the likelihood of this
    is generally controlled by the ``region_surcharge`` parameter).

    In any case where the surcharges are either not set or zero,
    this is effectively the same as calling random.choice() on the
    list of cuts. Under the above conditions, all of the weights
    on the cuts are randomly generated on the interval [0,1], and
    there is no outside force that might make the weight assigned
    to a particular type of cut higher than another.

    :param cut_edge_list: A list of Cut objects. Each object has an
        edge, a weight, and a subset attribute.
    :type cut_edge_list: List[Cut]

    :returns: The cut with the highest random weight.
    :rtype: Cut
    """

    # Just in case, default to random choice
    if not isinstance(cut_edge_list[0], Cut) or cut_edge_list[0].weight is None:
        return random.choice(cut_edge_list)

    # frm: ???:  this strikes me as possibly expensive.  Computing the
    #               max in a list is O(N) so not terrible, but this
    #               might be called lots of times (need to know more about
    #               how it is used).  Would it make sense to have the
    #               cut_edge_list sorted before it is frozen?  I think it
    #               is now a set, so it would need to be a list...  Not
    #               urgent, but worth looking into at some point...
    #
    return max(cut_edge_list, key=lambda cut: cut.weight)


# frm: TODO:  Documentation: document what _power_set_sorted_by_size_then_sum() does
#
#  Figure out what this does.  There is no NX/RX issue here, I just
#                   don't yet know what it does or why...
# Note that this is only ever used once...
def _power_set_sorted_by_size_then_sum(region_surcharge_dict: Dict):
    """
    This function computes the power set of regions that are
    listed in the region_surcharge_dict, and then sorts
    that power set by size and then sum.

    Note that a power set contains all possible subsets of
    a given set, so for instance, the power set of
    of elements of a given set

    :param region_surcharge_dict: Description
    :type region_surcharge_dict: Dict
    """
    num_regions = len(region_surcharge_dict)
    power_set = [
        s
        for i in range(1, num_regions + 1)
        for s in itertools.combinations(region_surcharge_dict.keys(), i)
    ]

    # Sort the subsets in descending order based on
    # the sum of their corresponding values in the dictionary
    sorted_power_set = sorted(
        power_set, key=lambda s: (len(s), sum(region_surcharge_dict[i] for i in s)), reverse=True
    )

    return sorted_power_set


# Note that the populated graph and the region surcharge are passed
# by object reference. This means that a copy is not made since we
# are not modifying the object in the function, and the speed of
# this randomized selection will not suffer for it.
def _region_preferred_max_weight_choice(
    populated_graph: PopulatedGraph, region_surcharge: Dict, cut_edge_list: List[Cut]
) -> Cut:
    # frm: ???:  There is no NX/RX dependency in this routine, but I do
    #               not yet understand what it does or why...
    """
    This function is used in the case of a region-aware chain. It
    is similar to the as :meth:`_max_weight_choice` function except
    that it will preferentially select one of the cuts that has the
    highest surcharge. So, if we have a weight dict of the form
    ``{region1: wt1, region2: wt2}`` , then this function first looks
    for a cut that is a cut edge for both ``region1`` and ``region2``
    and then selects the one with the highest weight. If no such cut
    exists, then it will then look for a cut that is a cut edge for the
    region with the highest surcharge (presumably the region that we care
    more about not splitting).

    In the case of 3 regions, it will first look for a cut that is a
    cut edge for all 3 regions, then for a cut that is a cut edge for
    2 regions sorted by the highest total surcharge, and then for a cut
    that is a cut edge for the region with the highest surcharge.

    For the case of 4 or more regions, the power set starts to get a bit
    large, so we default back to the :meth:`_max_weight_choice` function
    and just select the cut with the highest weight, which will still
    preferentially select for cuts that span the most regions that we
    care about.

    :param populated_graph: The populated graph.
    :type populated_graph: PopulatedGraph
    :param region_surcharge: A dictionary of surcharges for the spanning
        tree algorithm.
    :type region_surcharge: Dict
    :param cut_edge_list: A list of Cut objects. Each object has an
        edge, a weight, and a subset attribute.
    :type cut_edge_list: List[Cut]

    :returns: A random Cut from the set of possible Cuts with the highest
        surcharge.
    :rtype: Cut
    """
    if (
        not isinstance(region_surcharge, dict)
        or not isinstance(cut_edge_list[0], Cut)
        or cut_edge_list[0].weight is None
    ):
        return random.choice(cut_edge_list)

    # Early return for simple cases
    if len(region_surcharge) < 1 or len(region_surcharge) > 3:
        return _max_weight_choice(cut_edge_list)

    # Prepare data for efficient access
    edge_region_info = {
        cut: {
            # Given a cut_edge_list (whose elements have an
            # attribute, "edge",) construct a dict
            # that associates with each "cut" the
            # values of the region_surcharge values
            # for both nodes in the edge.
            #
            # So, if the region_surcharge dict was
            # {"muni": 0.2, "water": 0.8} then for
            # each cut, cut_n, there would be a
            # dict value that looked like:
            #
            #           {
            #             "muni": (<node_1_muni_weight>, <node_2_muni_weight>)
            #             "water": (<node_1_water_weight>, <node_2_water_weight>)
            #           }
            #
            key: (
                populated_graph.graph.node_data(cut.edge[0]).get(key),
                populated_graph.graph.node_data(cut.edge[1]).get(key),
            )
            for key in region_surcharge
        }
        for cut in cut_edge_list
    }

    # Generate power set sorted by surcharge, then filter cuts based
    # on region matching
    power_set = _power_set_sorted_by_size_then_sum(region_surcharge)
    for region_combination in power_set:
        suitable_cuts = [
            cut
            for cut in cut_edge_list
            if all(
                edge_region_info[cut][key][0] != edge_region_info[cut][key][1]
                for key in region_combination
            )
        ]
        if suitable_cuts:
            return _max_weight_choice(suitable_cuts)

    return _max_weight_choice(cut_edge_list)


# frm TODO: Refactoring:  How to prevent users writing custom code from getting screwed by RX...
#
# I am actually not sure if this is a real concern or not, but the issue is whether
# custom code that expects the graph object to be NX will get screwed up now that by default
# the embedded graph object in RX-based.
#
# The most obvious way custom code could screw up is by not dealing with subgraphs properly.
# It would be really nice to have some clever way to detect code that assumed it was dealing
# with NX and issue a warning, but I am not that clever...
#
# In most cases, the user will do something NX based that will trigger an error - such as
# accessing node or edge data using graph.nodes[node_id] instead of graph.node_data(node_id),
# so maybe this is not a huge issue...
#
# Peter wrote a comment in a PR that is applicable here, so I will include it for future
# reference:
#
#     Peter's comments from PR:
#
#     Users do sometimes write custom spanning tree and cut edge functions. My
#     recommendation would be to make this simple for now. Have a list of "RX_compatible"
#     functions and then have the MarkovChain class do some coersion to store an
#     appropriate graph and partition object at initialization. We always expect
#     the workflow to be something like
#
#         Graph -> Partition -> MarkovChain
#
#     But we do copy operations in each step, so I wouldn't expect any weird
#     side-effects from pushing the determination of what graph type to use
#     off onto the MarkovChain class
#
# I think I am now comfortable with leaving this as-is.  My logic is that if a
# user has written custom code then he/she will almost certainly use some NX
# idiom (like graph.nodes[node_id][attribute_name]) which will blow up, so
# he/she will be alerted that something is not right, and then look for help
# which the RX Migration Guide should provide.
#
# Peter - what do you think?

# frm: TODO: Refactoring: Consolidate logic into bipartition_tree()
#
# There are a couple of issues that would be really nice to resolve:
#
#   1) region_surcharge:
#
#      This is more of a documenation issue (I think).  The issue is that
#      it is not clear exactly how a region_surcharge affects the operation
#      of the bipartition_tree() algorithm.  We supply two spanning_tree
#      functions, uniform_spanning_tree() which uses Wilson's algorithm
#      and random_spanning_tree() which uses Kruskal's algorithm.  In fact,
#      both of these are "random" so the naming of the two routines is
#      unfortunate, but the real question is why we even bother to
#      provide uniform_spanning_tree() as an option.  In what cases would
#      it be preferable to random_spanning_tree()?
#
#      The first observation is that both functions are "random".  The
#      uniform_spanning_tree() function uses Wilson's algorithm which
#      is random all by itself.  The random_spanning_tree() function is
#      also random because it assigns random weights to edges and then
#      uses Kruskal's algorithm to pick a "minimal" spanning tree based
#      on those random weights.
#
#      The random_spanning_tree() function, however, can be biased to
#      preserve "regions" by passing in a "region_surcharge".
#
#      So, why do we need uniform_spanning_tree() at all?  What advantage
#      does it provide and in what circumstances?  I thought that it must
#      be performance, but the web implies that Kruskal's algorithm is
#      often faster than Wilson's algorithm especially for sparse graphs,
#      and I think GerryChain graphs are pretty sparse.  So why not just
#      get rid of uniform_spanning_tree?
#
#      It occurred to me that the shapes of the trees that result from
#      the two algorithms might differ - the simulations I saw of Kruskal's
#      algorithm seemed to create quite unbalanced trees which would perhaps
#      make it harder to find subtrees with the correct population.  Is this
#      a factor?
#
#      So, in the end, this is all about helping the user understand
#      when to use what spanning_tree function, and my guess is that
#      the answer is to always use random_spanning_tree() even if the
#      user is NOT providing a region_surcharge.
#
#      Peter: Is the above correct?  Is there, in fact, no reason
#             to provide uniform_spanning_tree()?
#
#      This all stemmed from an earlier thought that the code should
#      do a sanity check and warn the user if random_spanning_tree() was
#      called without supplying a region_surcharge.  I now think that
#      it should ALWAYS be called - regardless of whether there is a
#      region_surcharge.
#
#      In any event, I would still like to unify the function signatures
#      of the two spanning_tree functions and then insert a test
#      in uniform_spanning_tree() that issues a warning if the
#      region_surcharge passed in was not None.
#
#   2) one_sided_cut
#
#      I found the term "one_sided_cut" unintuitive, and I had to refresh my
#      memory every time I read the code to remember whether True meant carving
#      off a district or whether True meant split the graph into two "equal"
#      districts.
#
#      But, mostly, I would like to change the code in bipartition_tree() to make
#      it crystal clear to the user that it does two quite different things
#      depending on the value of this parameter.
#
#      I suggest creating two helper functions - one that "carves" away a district
#      and another that splits the graph into two "equal" districts.  This would
#      make it clear to a reader of the code what is going on.  Something like:
#
#          # setup variables needed by both helper functions
#          ...
#
#          if one_sided_cut:
#              carve_out_district(...)
#          else
#              split_into_two(...)
#
#   3) differet functions for doing bipartition_tree - I think we can get by with
#      a single function
#
#      At present, there are two bipartition_tree routines in the code (January 10, 2026).
#      The differences between them are small, and I believe it would be easy to unify
#      them into a single routine.  While this would make the unified routine more complex
#      I think it would make understanding what is going on overall simpler.  If you
#      understand what bipartition_tree() does, then you have a handle on everything that
#      GerryChain does and how it does it.  Everything else is just flow control and
#      book-keeping
#
# Get Peter's feedback on whether this all makes sense.


def old_bipartition_tree(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    region_surcharge: Optional[Dict] = None,
    balance_edge_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    choice: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
    warn_attempts: int = 1000,
    allow_pair_reselection: bool = False,
    cut_choice: Callable = _region_preferred_max_weight_choice,
) -> Set:
    # frm: TODO: Refactoring: Change the names of ALL function formal parameters to end
    #      in "_fn" - to make it clear that the paraemter is a function.  This will make it
    #      easier to do a global search to find all function parameters - as well as just being
    #      good coding practice...
    """
    This function finds a balanced 2 partition of a graph by drawing a
    spanning tree and finding an edge to cut that leaves at most an epsilon
    imbalance between the populations of the parts. If a root fails, new roots
    are tried until node_repeats in which case a new tree is drawn.

    Builds up a connected subgraph with a connected complement whose population
    is ``epsilon * pop_target`` away from ``pop_target``.

    :param graph: The graph to partition.
    :type graph: Graph
    :param pop_col: The node attribute holding the population of each node.
    :type pop_col: str
    :param pop_target: The target population for the returned subset of nodes.
    :type pop_target: Union[int, float]
    :param epsilon: The allowable deviation from ``pop_target`` (as a percentage of
        ``pop_target``) for the subgraph's population.
    :type epsilon: float
    :param node_repeats: A parameter for the algorithm: how many different choices
        of root to use before drawing a new spanning tree. Defaults to 1.
    :type node_repeats: int, optional
    :param spanning_tree: The spanning tree for the algorithm to use (used when the
        algorithm chooses a new root and for testing).
    :type spanning_tree: Optional[Graph], optional
    :param spanning_tree_fn: The random spanning tree algorithm to use if a spanning
        tree is not provided. Defaults to :func:`random_spanning_tree`.
    :type spanning_tree_fn: Callable, optional
    :param region_surcharge: A dictionary of surcharges for the spanning tree algorithm.
        Defaults to None.
    :type region_surcharge: Optional[Dict], optional
    :param balance_edge_fn: The function to find balanced edge cuts. Defaults to
        :func:`find_balanced_edge_cuts_memoization`.
    :type balance_edge_fn: Callable, optional
    :param one_sided_cut: Passed to the ``balance_edge_fn``. Determines whether or not we are
        cutting off a single district when partitioning the tree. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param choice: The function to make a random choice of root node for the population
        tree. Passed to ``balance_edge_fn``. Can be substituted for testing.
        Defaults to :func:`random.random()`.
    :type choice: Callable, optional
    :param max_attempts: The maximum number of attempts that should be made to bipartition.
        Defaults to 10000.
    :type max_attempts: Optional[int], optional
    :param warn_attempts: The number of attempts after which a warning is issued if a balanced
        cut cannot be found. Defaults to 1000.
    :type warn_attempts: int, optional
    :param allow_pair_reselection: Whether we would like to return an error to the calling
        function to ask it to reselect the pair of nodes to try and recombine. Defaults to False.
    :type allow_pair_reselection: bool, optional
    :param cut_choice: The function used to select the cut edge from the list of possible
        balanced cuts. Defaults to :meth:`_region_preferred_max_weight_choice` .
    :type cut_choice: Callable, optional

    :returns: A subset of nodes of ``graph`` (whose induced subgraph is connected). The other
        part of the partition is the complement of this subset.
    :rtype: Set

    :raises BipartitionWarning: If a possible cut cannot be found after 1000 attempts.
    :raises RuntimeError: If a possible cut cannot be found after the maximum number of attempts
        given by ``max_attempts``.
    """
    # Try to add the region-aware in if the spanning_tree_fn accepts a surcharge dictionary
    # frm ???:  REALLY???  You are going to change the semantics of your program based on the
    #           a function argument's signature?  What if someone refactors the code to have
    #           different names???  *sigh*
    #
    # A better strategy would be to lock in the function signature for ALL spanning_tree
    # functions and then just have the region_surcharge parameter not be used in some of them...
    #
    # Same with "one_sided_cut"
    #
    # Oh - and change "one_sided_cut" to be something a little more intuitive.  I have to
    # reset my mind every time I see it to figure out whether it means to split into
    # two districts or just peel off one district...  *sigh*  Before doing this, check to
    # see if "one_sided_cut" is a term of art that might make sense to some set of experts...
    #
    if "region_surcharge" in signature(spanning_tree_fn).parameters:
        spanning_tree_fn = partial(spanning_tree_fn, region_surcharge=region_surcharge)

    if "one_sided_cut" in signature(balance_edge_fn).parameters:
        balance_edge_fn = partial(balance_edge_fn, one_sided_cut=one_sided_cut)

    # dict of node_id: population for the nodes in the subgraph
    populations = {
        node_id: subgraph_to_split.node_data(node_id)[pop_col]
        for node_id in subgraph_to_split.node_indices
    }

    possible_cuts: List[Cut] = []
    if spanning_tree is None:
        spanning_tree = spanning_tree_fn(subgraph_to_split)

    restarts = 0
    attempts = 0

    while max_attempts is None or attempts < max_attempts:
        if restarts == node_repeats:
            spanning_tree = spanning_tree_fn(subgraph_to_split)
            restarts = 0
        h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)

        # frm: TODO: Refactoring:  Again - we should NOT be changing semantics based
        #                   on the names in signatures...
        # Better approach is to have all of the poosible paramters exist
        # in ALL of the versions of the cut_choice() functions and to
        # have them default to None if not used by one of the functions.
        # Then this code could just pass in the values to the
        # cut_choice function, and it could make sense of what to do.
        #
        # This makes it clear what the overall and comprehensive purpose
        # of cut_choice functions are.  This centralizes the knowlege
        # of what a cut_choice() function is supposed to do - or at least
        # it prompts the programmer to document that a param in the
        # general scheme does not apply in a given instance.
        #
        # I realize that this is perhaps not "pythonic" - in that it
        # forces the programmer to document overall behavior instead
        # of just finding a convenient way to sneak in something new.
        # However, when code gets complicated, sneaky/clever code
        # is just not worth it - better to have each change be a little
        # more painful (needing to change the function signature for
        # all instances of a generic function to add new functionality
        # that is only needed by one new instance).  This provides
        # a natural place (in comments of the generic function instances)
        # to describe what is going on - and it alerts programmers
        # that a given generic function has perhaps many different
        # instances - but that they all share the same high level
        # responsibility.

        # frm:  Find one or more edges in the spanning tree, that if cut would
        #       result in a subtree with the appropriate population.

        # This returns a list of Cut objects with attributes edge and subset
        possible_cuts = balance_edge_fn(h, choice=choice)

        is_region_cut = (
            "region_surcharge" in signature(cut_choice).parameters
            and "populated_graph" in signature(cut_choice).parameters
        )

        if len(possible_cuts) != 0:

            chosen_cut = None
            if is_region_cut:
                chosen_cut = cut_choice(h, region_surcharge, possible_cuts)
            else:
                chosen_cut = cut_choice(possible_cuts)

            translated_nodes = subgraph_to_split.translate_subgraph_node_ids_for_set_of_nodes(
                chosen_cut.subset
            )
            # frm: Not sure if it is important that the returned set be a frozenset...
            return frozenset(translated_nodes)

        restarts += 1
        attempts += 1

        # Don't forget to change the documentation if you change this number
        if attempts == warn_attempts and not allow_pair_reselection:
            warnings.warn(
                f"\nFailed to find a balanced cut after {warn_attempts} attempts.\n"
                "If possible, consider enabling pair reselection within your\n"
                "MarkovChain proposal method to allow the algorithm to select\n"
                "a different pair of districts for recombination.",
                BipartitionWarning,
            )

    # frm: TODO: Refactoring:  raise ReselectException seems evil...
    #
    # I was taught that raising exceptions should be for bad things, not for
    # clever logic for "normal" situations.  In this case, raising this exception
    # allows recom() - and only recom() to detect that this pair of districts
    # didn't work out so it should try a different pair.
    #
    # Why not just return None - doing that would signal that no bipartition
    # was found which is exactly what this exception signals.  It just seenms
    # odd to have a function use an exception as the way to return a result-code.
    #
    # Am I being old-fashioned?  Is this the new Pythonic way of doing things?

    if allow_pair_reselection:
        raise ReselectException(
            f"Failed to find a balanced cut after {max_attempts} attempts.\n"
            f"Selecting a new district pair."
        )

    raise RuntimeError(f"Could not find a possible cut after {max_attempts} attempts.")


##################################
# Start of new code:


def bipartition_tree(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    region_surcharge: Optional[Dict] = None,
    balance_edge_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    choice: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
    warn_attempts: int = 1000,
    allow_pair_reselection: bool = False,
    cut_choice: Callable = _region_preferred_max_weight_choice,
) -> Set:
    # frm: TODO: Refactoring: Change the names of ALL function formal parameters to end
    #      in "_fn" - to make it clear that the paraemter is a function.  This will make it
    #      easier to do a global search to find all function parameters - as well as just being
    #      good coding practice...
    """
    This function finds a balanced 2 partition of a graph by drawing a
    spanning tree and finding an edge to cut that leaves at most an epsilon
    imbalance between the populations of the parts. If a root fails, new roots
    are tried until node_repeats in which case a new tree is drawn.

    Builds up a connected subgraph with a connected complement whose population
    is ``epsilon * pop_target`` away from ``pop_target``.

    :param graph: The graph to partition.
    :type graph: Graph
    :param pop_col: The node attribute holding the population of each node.
    :type pop_col: str
    :param pop_target: The target population for the returned subset of nodes.
    :type pop_target: Union[int, float]
    :param epsilon: The allowable deviation from ``pop_target`` (as a percentage of
        ``pop_target``) for the subgraph's population.
    :type epsilon: float
    :param node_repeats: A parameter for the algorithm: how many different choices
        of root to use before drawing a new spanning tree. Defaults to 1.
    :type node_repeats: int, optional
    :param spanning_tree: The spanning tree for the algorithm to use (used when the
        algorithm chooses a new root and for testing).
    :type spanning_tree: Optional[Graph], optional
    :param spanning_tree_fn: The random spanning tree algorithm to use if a spanning
        tree is not provided. Defaults to :func:`random_spanning_tree`.
    :type spanning_tree_fn: Callable, optional
    :param region_surcharge: A dictionary of surcharges for the spanning tree algorithm.
        Defaults to None.
    :type region_surcharge: Optional[Dict], optional
    :param balance_edge_fn: The function to find balanced edge cuts. Defaults to
        :func:`find_balanced_edge_cuts_memoization`.
    :type balance_edge_fn: Callable, optional
    :param one_sided_cut: Passed to the ``balance_edge_fn``. Determines whether or not we are
        cutting off a single district when partitioning the tree. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param choice: The function to make a random choice of root node for the population
        tree. Passed to ``balance_edge_fn``. Can be substituted for testing.
        Defaults to :func:`random.random()`.
    :type choice: Callable, optional
    :param max_attempts: The maximum number of attempts that should be made to bipartition.
        Defaults to 10000.
    :type max_attempts: Optional[int], optional
    :param warn_attempts: The number of attempts after which a warning is issued if a balanced
        cut cannot be found. Defaults to 1000.
    :type warn_attempts: int, optional
    :param allow_pair_reselection: Whether we would like to return an error to the calling
        function to ask it to reselect the pair of nodes to try and recombine. Defaults to False.
    :type allow_pair_reselection: bool, optional
    :param cut_choice: The function used to select the cut edge from the list of possible
        balanced cuts. Defaults to :meth:`_region_preferred_max_weight_choice` .
    :type cut_choice: Callable, optional

    :returns: A subset of nodes of ``graph`` (whose induced subgraph is connected). The other
        part of the partition is the complement of this subset.
    :rtype: Set

    :raises BipartitionWarning: If a possible cut cannot be found after 1000 attempts.
    :raises RuntimeError: If a possible cut cannot be found after the maximum number of attempts
        given by ``max_attempts``.
    """
    # Try to add the region-aware in if the spanning_tree_fn accepts a surcharge dictionary
    # frm ???:  REALLY???  You are going to change the semantics of your program based on the
    #           a function argument's signature?  What if someone refactors the code to have
    #           different names???  *sigh*
    #
    # A better strategy would be to lock in the function signature for ALL spanning_tree
    # functions and then just have the region_surcharge parameter not be used in some of them...
    #
    # Same with "one_sided_cut"
    #
    # Oh - and change "one_sided_cut" to be something a little more intuitive.  I have to
    # reset my mind every time I see it to figure out whether it means to split into
    # two districts or just peel off one district...  *sigh*  Before doing this, check to
    # see if "one_sided_cut" is a term of art that might make sense to some set of experts...
    #
    if "region_surcharge" in signature(spanning_tree_fn).parameters:
        spanning_tree_fn = partial(spanning_tree_fn, region_surcharge=region_surcharge)

    if "one_sided_cut" in signature(balance_edge_fn).parameters:
        balance_edge_fn = partial(balance_edge_fn, one_sided_cut=one_sided_cut)

    # Find possible edge cuts if they exist.
    #
    # Note that _get_possible_edge_cuts_and_populated_graph() will raise and exception if max_attempts is exceeded.
    #
    cuts_and_populated_graph = _get_possible_edge_cuts_and_populated_graph(
        subgraph_to_split,
        pop_col,
        pop_target,
        epsilon,
        node_repeats=node_repeats,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        balance_edge_fn=balance_edge_fn,
        choice=choice,
        max_attempts=max_attempts,
        warn_attempts=warn_attempts,
        repeat_until_valid=True,
        allow_pair_reselection=allow_pair_reselection,
    )
    possible_cuts = cuts_and_populated_graph[0]
    populated_graph = cuts_and_populated_graph[1]

    # frm: TODO: Refactoring:  Think about whether we should pass warn_attempts to other calls on _get_possible_edge_cuts_and_populated_graph()

    if len(possible_cuts) != 0:

        is_region_cut = (
            "region_surcharge" in signature(cut_choice).parameters
            and "populated_graph" in signature(cut_choice).parameters
        )

        chosen_cut = None
        if is_region_cut:
            chosen_cut = cut_choice(populated_graph, region_surcharge, possible_cuts)
        else:
            chosen_cut = cut_choice(possible_cuts)

        translated_nodes = subgraph_to_split.translate_subgraph_node_ids_for_set_of_nodes(
            chosen_cut.subset
        )
        # frm: Not sure if it is important that the returned set be a frozenset...
        return frozenset(translated_nodes)

    else:
        # frm: TODO: Refactoring: Clean this up...
        raise Exception("This should never happen...")

        # frm: TODO: Refactoring:  Again - we should NOT be changing semantics based
        #                   on the names in signatures...
        # Better approach is to have all of the poosible paramters exist
        # in ALL of the versions of the cut_choice() functions and to
        # have them default to None if not used by one of the functions.
        # Then this code could just pass in the values to the
        # cut_choice function, and it could make sense of what to do.
        #
        # This makes it clear what the overall and comprehensive purpose
        # of cut_choice functions are.  This centralizes the knowlege
        # of what a cut_choice() function is supposed to do - or at least
        # it prompts the programmer to document that a param in the
        # general scheme does not apply in a given instance.
        #
        # I realize that this is perhaps not "pythonic" - in that it
        # forces the programmer to document overall behavior instead
        # of just finding a convenient way to sneak in something new.
        # However, when code gets complicated, sneaky/clever code
        # is just not worth it - better to have each change be a little
        # more painful (needing to change the function signature for
        # all instances of a generic function to add new functionality
        # that is only needed by one new instance).  This provides
        # a natural place (in comments of the generic function instances)
        # to describe what is going on - and it alerts programmers
        # that a given generic function has perhaps many different
        # instances - but that they all share the same high level
        # responsibility.

    # frm: TODO: Refactoring:  raise ReselectException seems evil...
    #
    # I was taught that raising exceptions should be for bad things, not for
    # clever logic for "normal" situations.  In this case, raising this exception
    # allows recom() - and only recom() to detect that this pair of districts
    # didn't work out so it should try a different pair.
    #
    # Why not just return None - doing that would signal that no bipartition
    # was found which is exactly what this exception signals.  It just seenms
    # odd to have a function use an exception as the way to return a result-code.
    #
    # Am I being old-fashioned?  Is this the new Pythonic way of doing things?


# End of new code:1
##################################


def _get_possible_edge_cuts_and_populated_graph(
    #
    # Note: Complexity Alert...  _get_possible_edge_cuts_and_populated_graph does NOT translate
    # node_ids to parent
    #
    # Unlike many/most of the routines in this module, _get_possible_edge_cuts_and_populated_graph() does
    # not translate node_ids into the IDs of the parent, because calls to it are not made
    # on subgraphs.  That is, it returns possible Cuts using the same node_ids as the parent.
    # It is up to the caller to translate node_ids (if appropriate).
    #
    # As stated somewhere else, I would love to change the name of this function so that
    # it does not potentially confuse the reader that it is the same as the other
    # bipartition_tree functions.
    graph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    balance_edge_fn: Callable = find_balanced_edge_cuts_memoization,
    choice: Callable = random.choice,
    repeat_until_valid: bool = True,
    warn_attempts: int = 1000,
    max_attempts: Optional[int] = 100000,
    allow_pair_reselection: bool = False,
) -> tuple[List[Cut], PopulatedGraph]:
    """
    Randomly bipartitions a tree into two subgraphs until a valid bipartition is found.

    :param graph: The input graph.
    :type graph: Graph
    :param pop_col: The name of the column in the graph nodes that contains the population data.
    :type pop_col: str
    :param pop_target: The target population for each subgraph.
    :type pop_target: Union[int, float]
    :param epsilon: The allowed deviation from the target population as a percentage of
        pop_target.
    :type epsilon: float
    :param node_repeats: The number of times to repeat the bipartitioning process. Defaults to 1.
    :type node_repeats: int, optional
    :param repeat_until_valid: Whether to repeat the bipartitioning process until a valid
        bipartition is found. Defaults to True.
    :type repeat_until_valid: bool, optional
    :param spanning_tree: The spanning tree to use for bipartitioning. If None, a random spanning
        tree will be generated. Defaults to None.
    :type spanning_tree: Optional[Graph], optional
    :param spanning_tree_fn: The function to generate a spanning tree. Defaults to
        random_spanning_tree.
    :type spanning_tree_fn: Callable, optional
    :param balance_edge_fn: The function to find balanced edge cuts. Defaults to
        find_balanced_edge_cuts_memoization.
    :type balance_edge_fn: Callable, optional
    :param choice: The function to choose a random element from a list. Defaults to random.choice.
    :type choice: Callable, optional
    :param max_attempts: The maximum number of attempts to find a valid bipartition. If None,
        there is no limit. Defaults to None.
    :type max_attempts: Optional[int], optional

    :returns: A tuple with a list of possible cuts that bipartition the tree into two subgraphs and
        the PopulatedGraph the cuts were obtained from.
    :rtype: tuple[List[Tuple[Hashable, Hashable]], PopulatedGraph]

    :raises RuntimeError: If a valid bipartition cannot be found after the specified number of
        attempts.
    """

    # dict of node_id: population for the nodes in the subgraph
    populations = {
        node_id: graph_to_split.node_data(node_id)[pop_col]
        for node_id in graph_to_split.node_indices
    }

    possible_cuts = []
    if spanning_tree is None:
        spanning_tree = spanning_tree_fn(graph_to_split)

    restarts = 0
    attempts = 0

    # frm: TODO: Code: When would it make sense for max_attempts to be None?  Infinite loop potential...
    while max_attempts is None or attempts < max_attempts:
        if restarts == node_repeats:
            spanning_tree = spanning_tree_fn(graph_to_split)
            restarts = 0
        h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)
        possible_cuts = balance_edge_fn(h, choice=choice)

        # frm: TODO: Refactoring: change name of repeat_until_valid and think a bit...
        #
        # There is only one tine in the GerryCode codebase where "repeat_until_valid" is set
        # to False, and that is in reversible_recom().  What I think is really going on is
        # that in reversible_recom() and ONLY in reversible_recom(), we want to try once to
        # get the cuts but to fail if we don't get it on the first try.  I do not understand
        # the logic of reversible_recom() well enough to know if this is 100% accurate, but
        # the point remains that what repeat_until_valid really means is "only_try_one_time".
        #
        # I would also argue against the boolean logic here - needlessly complex.  What
        # would make more sense to me is:
        #
        #     if (not repeat_until_valid):
        #         return possible_cuts
        #     elif len(possible_cuts) != 0:
        #         return possible_cuts
        #
        # or if you change the name of repeat_until_valid:
        #
        #     only_try_one_time = not repeat_until_valid   # clarify what param means...
        #     if (only_try_one_time):
        #         return possible_cuts    # return even if possible_cuts is None
        #     elif len(possible_cuts) != 0:
        #         return possible_cuts
        #
        # I realize that repeat_until_valid could be interpreted as do_not_return_None, but that
        # was not my initial understanding - I thought it meant "keep iterating forever".  My
        # initial reaction was "uh oh - infinite loop danger".
        #
        # So, not quite sure what the right name is for this param, but it took me a while to
        # convince myself that the code made sense.
        #

        # In the case of reversible_recom, we are OK returning None.
        if not repeat_until_valid:
            return (possible_cuts, h)

        # If we have found at least one possible cut, return
        if len(possible_cuts) != 0:
            return (possible_cuts, h)

        # Don't forget to change the documentation if you change this number
        if attempts == warn_attempts and not allow_pair_reselection:
            warnings.warn(
                f"\nFailed to find a balanced cut after {warn_attempts} attempts.\n"
                "If possible, consider enabling pair reselection within your\n"
                "MarkovChain proposal method to allow the algorithm to select\n"
                "a different pair of districts for recombination.",
                BipartitionWarning,
            )

        restarts += 1
        attempts += 1

    # frm: TODO: Refactoring:  raise ReselectException seems evil...
    #
    # I was taught that raising exceptions should be for bad things, not for
    # clever logic for "normal" situations.  In this case, raising this exception
    # allows recom() - and only recom() to detect that this pair of districts
    # didn't work out so it should try a different pair.
    #
    # Why not just return None - doing that would signal that no bipartition
    # was found which is exactly what this exception signals.  It just seenms
    # odd to have a function use an exception as the way to return a result-code.
    #
    # Am I being old-fashioned?  Is this the new Pythonic way of doing things?

    if allow_pair_reselection:
        raise ReselectException(
            f"Failed to find a balanced cut after {max_attempts} attempts.\n"
            f"Selecting a new district pair."
        )

    raise RuntimeError(f"Could not find a possible cut after {max_attempts} attempts.")


# frm: used in this file and in tree_proposals.py
#       But maybe this is intended to be used externally...


#######################
# frm: Note:  This routine is EXACTLY the same as bipartition_tree_random() except
#               that it returns in addition to the nodes for a new district, the
#               number of possible new districts.  This additional information
#               is needed by reversible_recom(), but I did not want to change the
#               function signature of bipartition_tree_random() in case it is used
#               as part of the public API by someone.
#
#               It is bad form to have two functions that are the same excpet for
#               a tweak - an invitation for future bugs when you fix something in
#               one place and not the other, so maybe this is something we should
#               revisit when we decide a general code cleanup is in order...
#
def bipartition_tree_random_with_num_cuts(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    repeat_until_valid: bool = True,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    balance_edge_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    choice: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
) -> Union[Set[Any], None]:
    """
    This is like :func:`bipartition_tree` except it chooses a random balanced
    cut, rather than the first cut it finds.

    This function finds a balanced 2 partition of a graph by drawing a
    spanning tree and finding an edge to cut that leaves at most an epsilon
    imbalance between the populations of the parts. If a root fails, new roots
    are tried until node_repeats in which case a new tree is drawn.

    Builds up a connected subgraph with a connected complement whose population
    is ``epsilon * pop_target`` away from ``pop_target``.

    :param subgraph_to_split: The graph to partition.
    :type subgraph_to_split: Graph
    :param pop_col: The node attribute holding the population of each node.
    :type pop_col: str
    :param pop_target: The target population for the returned subset of nodes.
    :type pop_target: Union[int, float]
    :param epsilon: The allowable deviation from  ``pop_target`` (as a percentage of
        ``pop_target``) for the subgraph's population.
    :type epsilon: float
    :param node_repeats: A parameter for the algorithm: how many different choices
        of root to use before drawing a new spanning tree. Defaults to 1.
    :type node_repeats: int
    :param repeat_until_valid: Determines whether to keep drawing spanning trees
        until a tree with a balanced cut is found. If `True`, a set of nodes will
        always be returned; if `False`, `None` will be returned if a valid spanning
        tree is not found on the first try. Defaults to True.
    :type repeat_until_valid: bool, optional
    :param spanning_tree: The spanning tree for the algorithm to use (used when the
        algorithm chooses a new root and for testing). Defaults to None.
    :type spanning_tree: Optional[Graph], optional
    :param spanning_tree_fn: The random spanning tree algorithm to use if a spanning
        tree is not provided. Defaults to :func:`random_spanning_tree`.
    :type spanning_tree_fn: Callable, optional
    :param balance_edge_fn: The algorithm used to find balanced cut edges. Defaults to
        :func:`find_balanced_edge_cuts_memoization`.
    :type balance_edge_fn: Callable, optional
    :param one_sided_cut: Passed to the ``balance_edge_fn``. Determines whether or not we are
        cutting off a single district when partitioning the tree. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param choice: The random choice function. Can be substituted for testing. Defaults
        to :func:`random.choice`.
    :type choice: Callable, optional
    :param max_attempts: The max number of attempts that should be made to bipartition.
        Defaults to None.
    :type max_attempts: Optional[int], optional

    :returns: A subset of nodes of ``graph`` (whose induced subgraph is connected) or None if a
        valid spanning tree is not found.
    :rtype: Union[Set[Any], None]
    """

    # frm: TODO: Refactoring:  Again - semantics should not depend on signatures...
    if "one_sided_cut" in signature(balance_edge_fn).parameters:
        balance_edge_fn = partial(balance_edge_fn, one_sided_cut=True)

    cuts_and_populated_graph = _get_possible_edge_cuts_and_populated_graph(
        graph_to_split=subgraph_to_split,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        repeat_until_valid=repeat_until_valid,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        balance_edge_fn=balance_edge_fn,
        choice=choice,
        max_attempts=max_attempts,
    )
    possible_cuts = cuts_and_populated_graph[0]

    if possible_cuts:
        chosen_cut = choice(possible_cuts)
        num_cuts = len(possible_cuts)
        parent_nodes = subgraph_to_split.translate_subgraph_node_ids_for_set_of_nodes(
            chosen_cut.subset
        )
        return num_cuts, frozenset(parent_nodes)  # frm: Not sure if important that it be frozenset
    else:
        return None


#######################
# frm * TODO:  Testing: Check to make sure there is a test for this...
def bipartition_tree_random(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    repeat_until_valid: bool = True,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    balance_edge_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    choice: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
) -> Union[Set[Any], None]:
    # frm: TODO: Documentation: Add docstrings...
    #
    # The docstrings should probably just defer to bipartition_tree_random_with_num_cuts()
    # with just an overview of what is going on.
    #

    # bipartition_tree_random_with_num_cuts() does what we want and more.
    # so call it and then just disregard the num_cuts, which we don't care about...
    #
    num_cuts, node_ids = bipartition_tree_random_with_num_cuts(
        subgraph_to_split=subgraph_to_split,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        repeat_until_valid=repeat_until_valid,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        balance_edge_fn=balance_edge_fn,
        one_sided_cut=one_sided_cut,
        choice=choice,
        max_attempts=max_attempts,
    )
    return node_ids


# frm: TODO: Refactoring: Remove old_bipartition_tree_random() after PR code review
#
# A while ago I added the routine, bipartition_tree_random_with_num_cuts() because
# the routine, reversible_recom() in tree_proposals.py had used an internal routine
# called _get_possible_edge_cuts_and_populated_graph() because it wanted to know how many possible
# cut solutions existed.  I did what was expedient and just added a function inside
# tree.py that did what the code in tree_proposals.py did in order to hide the
# internal routine.  I later realized that it was EXACTLY the same as bipartition_tree_random()
# except that it passed back one more value, so I just replaced the definitioin of
# bipartition_tree_random() with a call to bipartition_tree_random_with_num_cuts() and
# then discarded the extra num_cuts returned value.
#
# I am leaving this in the codebase for now, just to make it easier for Peter to see
# what is going on when he does a review.  Note that after this change all tests passed
# (January 9, 20206)
#
def old_bipartition_tree_random(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    repeat_until_valid: bool = True,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    balance_edge_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    choice: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
) -> Union[Set[Any], None]:
    """
    This is like :func:`bipartition_tree` except it chooses a random balanced
    cut, rather than the first cut it finds.

    This function finds a balanced 2 partition of a graph by drawing a
    spanning tree and finding an edge to cut that leaves at most an epsilon
    imbalance between the populations of the parts. If a root fails, new roots
    are tried until node_repeats in which case a new tree is drawn.

    Builds up a connected subgraph with a connected complement whose population
    is ``epsilon * pop_target`` away from ``pop_target``.

    :param graph: The graph to partition.
    :type graph: Graph
    :param pop_col: The node attribute holding the population of each node.
    :type pop_col: str
    :param pop_target: The target population for the returned subset of nodes.
    :type pop_target: Union[int, float]
    :param epsilon: The allowable deviation from  ``pop_target`` (as a percentage of
        ``pop_target``) for the subgraph's population.
    :type epsilon: float
    :param node_repeats: A parameter for the algorithm: how many different choices
        of root to use before drawing a new spanning tree. Defaults to 1.
    :type node_repeats: int
    :param repeat_until_valid: Determines whether to keep drawing spanning trees
        until a tree with a balanced cut is found. If `True`, a set of nodes will
        always be returned; if `False`, `None` will be returned if a valid spanning
        tree is not found on the first try. Defaults to True.
    :type repeat_until_valid: bool, optional
    :param spanning_tree: The spanning tree for the algorithm to use (used when the
        algorithm chooses a new root and for testing). Defaults to None.
    :type spanning_tree: Optional[Graph], optional
    :param spanning_tree_fn: The random spanning tree algorithm to use if a spanning
        tree is not provided. Defaults to :func:`random_spanning_tree`.
    :type spanning_tree_fn: Callable, optional
    :param balance_edge_fn: The algorithm used to find balanced cut edges. Defaults to
        :func:`find_balanced_edge_cuts_memoization`.
    :type balance_edge_fn: Callable, optional
    :param one_sided_cut: Passed to the ``balance_edge_fn``. Determines whether or not we are
        cutting off a single district when partitioning the tree. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param choice: The random choice function. Can be substituted for testing. Defaults
        to :func:`random.choice`.
    :type choice: Callable, optional
    :param max_attempts: The max number of attempts that should be made to bipartition.
        Defaults to None.
    :type max_attempts: Optional[int], optional

    :returns: A subset of nodes of ``graph`` (whose induced subgraph is connected) or None if a
        valid spanning tree is not found.
    :rtype: Union[Set[Any], None]
    """

    # frm: TODO: Refactoring:  Again - semantics should not depend on signatures...
    #
    # This is odd - there are two balance_edge_functions defined in tree.py but
    # both of them have a formal parameter with the name "one_sided_cut", so this
    # code is not picking one of them.  Perhaps there was an earlier version of
    # the code where it allowed functions that did not support "one_sided_cut".
    # In any event, it looks like this if-stmt is a no-op as far as the current
    # codebase is concerned...
    #
    # Even odder - there is a formal parameter, one_sided_cut, which is never
    # used...

    if "one_sided_cut" in signature(balance_edge_fn).parameters:
        balance_edge_fn = partial(balance_edge_fn, one_sided_cut=True)

    cuts_and_populated_graph = _get_possible_edge_cuts_and_populated_graph(
        graph_to_split=subgraph_to_split,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        repeat_until_valid=repeat_until_valid,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        balance_edge_fn=balance_edge_fn,
        choice=choice,
        max_attempts=max_attempts,
    )
    possible_cuts = cuts_and_populated_graph[0]
    if possible_cuts:
        chosen_cut = choice(possible_cuts)
        translated_nodes = subgraph_to_split.translate_subgraph_node_ids_for_set_of_nodes(
            chosen_cut.subset
        )
        return frozenset(translated_nodes)  # frm: Not sure if important that it be frozenset


# frm: TODO: Refactoring:  Would be nice to rename "method" to "bipartition_tree_method"
#
# This is clearly not a high priority, but it would be nice to have a parameter name that
# better stated what it meant.  "method" indicates that it is a function, but what does
# the function do?  When reading the code where "method" is called, it would have been
# nice to see bipartition_tree_method(...) instead.
#
# However, for legacy code reasons it is probably not worth changing.  *sigh*
#
# Peter - please confirm that this is not something that is worth changing, and
# then I will be able to put it behind me ;-).


def epsilon_tree_bipartition(
    subgraph_to_split: Graph,
    parts: Sequence,
    pop_target: Union[float, int],
    pop_col: str,
    epsilon: float,
    node_repeats: int = 1,
    method: Callable = partial(bipartition_tree, max_attempts=10000),
) -> Dict:
    """
    Uses :func:`~gerrychain.tree.bipartition_tree` to partition a tree into
    two parts of population ``pop_target`` (within ``epsilon``).

    :param graph: The graph to partition into two :math:`\varepsilon`-balanced parts.
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
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.bipartition_tree` to use.
        Defaults to 1.
    :type node_repeats: int, optional
    :param method: The partition method to use. Defaults to
        `partial(bipartition_tree, max_attempts=10000)`.
    :type method: Callable, optional

    :returns: New assignments for the nodes of ``graph``.
    :rtype: dict
    """
    if len(parts) != 2:
        raise ValueError(
            "This function only supports bipartitioning. Please ensure that there"
            + " are exactly 2 parts in the parts list."
        )

    flips = {}
    remaining_nodes = subgraph_to_split.node_indices

    lb_pop = pop_target * (1 - epsilon)
    ub_pop = pop_target * (1 + epsilon)
    check_pop = lambda x: lb_pop <= x <= ub_pop

    nodes = method(
        subgraph_to_split.subgraph(remaining_nodes),
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        one_sided_cut=False,
    )

    if nodes is None:
        raise BalanceError()

    # Calculate the total population for the two districts based on the
    # results of the "method()" partitioning.
    part_pop = 0
    for node in nodes:
        # frm: ???:  The code above has already confirmed that len(parts) is 2
        #               so why use negative index values - why not just use
        #               parts[0] and parts[1]?
        flips[node] = parts[-2]
        part_pop += subgraph_to_split.node_data(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    remaining_nodes -= nodes

    # All of the remaining nodes go in the last part
    part_pop = 0
    for node in remaining_nodes:
        flips[node] = parts[-1]
        part_pop += subgraph_to_split.node_data(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    # translate subgraph node_ids back into node_ids in parent graph
    translated_flips = subgraph_to_split.translate_subgraph_node_ids_for_flips(flips)

    return translated_flips


# frm: TODO: Refactoring: Move functions that create initial assignments to partition,py
#
# The two routines, recursive_tree_part() and recursive_seed_part() do not really have
# anything to do with tree algorithms  It is true that the USE tree algorighms, but
# they are not generally useful tree routines.
#
# They exist in order to create initial assignments to use to create a Partition object.
# As such they should live in partition.py.  This will have two nice effects:
#
#   1) They will live in the same module where they "belong" - the reader of code in
#      partition.py knows about assignments and can see routines that need assignments
#      so it makes perfect sense to include routines that create assignments there.
#
#   2) It will declutter tree.py which is already complex and hard to understand
#
# This may cause legacy users some pain if they use these routines in code that does
# not already import partition, but the error message should be clear enough to let them
# figure it out easily.


def recursive_tree_part(
    graph: Graph,
    parts: Sequence,
    pop_target: Union[float, int],
    pop_col: str,
    epsilon: float,
    node_repeats: int = 1,
    method: Callable = partial(bipartition_tree, max_attempts=10000),
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
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.bipartition_tree` to use.
        Defaluts to 1.
    :type node_repeats: int, optional
    :param method: The partition method to use. Defaults to
        `partial(bipartition_tree, max_attempts=10000)`.
    :type method: Callable, optional

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
    #                       the number of partitions desired) by calling the "method"
    #                       function, whose job it is to produce a connected set of
    #                       nodes that has the desired population target.
    #
    #                       Note that it sets one_sided_cut=True which tells the
    #                       "method" function that it is NOT bisecting the graph
    #                       but is rather supposed to just find one connected
    #                       set of nodes of the correct population size.

    for part in parts[:-2]:
        min_pop = max(pop_target * (1 - epsilon), pop_target * (1 - epsilon) - debt)
        max_pop = min(pop_target * (1 + epsilon), pop_target * (1 + epsilon) - debt)
        new_pop_target = (min_pop + max_pop) / 2

        try:
            node_ids = method(
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
        for node in node_ids:
            flips[node] = part
            part_pop += graph.node_data(node)[pop_col]

        if not check_pop(part_pop):
            raise PopulationBalanceError()

        debt += part_pop - pop_target
        remaining_nodes -= node_ids

    # After making n-2 districts, we need to make sure that the last
    # two districts are both balanced.

    # frm: For the last call to "method", set one_sided_cut=False to
    #       request that "method" create two equal sized districts
    #       with the given population goal by bisecting the graph.
    node_ids = method(
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
        # frm: this code fragment: graph.node_data(node_id)[pop_col] is used
        #       many times and is a candidate for being wrapped with
        #       a function that has a meaningful name, such as perhaps:
        #       get_population_for_node(node_id, pop_col).
        #       This is an example of code-bloat from the perspective of
        #       code gurus, but it really helps a new code reviewer understand
        #       WTF is going on...
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
    method: Callable = partial(bipartition_tree_random, max_attempts=10000),
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
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.bipartition_tree_random`
        to use. Defaults to 1.
    :type node_repeats: int, optional
    :param method: The method to use for bipartitioning the graph.
        Defaults to :func:`~gerrychain.tree_methods.bipartition_tree_random`
    :type method: Callable, optional

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

            nodes = method(
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
    method: Callable = partial(bipartition_tree, max_attempts=10000),
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
    :param method: Function used to find balanced partitions at the 2-district level.
        Defaults to :func:`~gerrychain.tree_methods.bipartition_tree`
    :type method: Callable, optional
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.bipartition_tree` to use.
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
        nodes = method(
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
        nodes = method(
            graph.subgraph(remaining_nodes),
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            node_repeats=node_repeats,
            one_sided_cut=True,
        )
        remaining_nodes -= nodes
        # frm: Create a list with the set of nodes returned by method() and then recurse
        #       to get the rest of the sets of nodes for remaining districts.
        assignment = [nodes] + _recursive_seed_part_inner(
            graph.subgraph(remaining_nodes),
            num_dists - 1,
            pop_target,
            pop_col,
            epsilon,
            method,
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
            method=partial(method, one_sided_cut=True),
        )

        assignment = []
        for chunk in chunks:
            chunk_assignment = _recursive_seed_part_inner(
                graph.subgraph(chunk),
                num_dists // num_chunks,  # new target number of districts
                pop_target,
                pop_col,
                epsilon,
                method,
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


def recursive_seed_part(
    graph: Graph,
    parts: Sequence,
    pop_target: Union[float, int],
    pop_col: str,
    epsilon: float,
    method: Callable = partial(bipartition_tree, max_attempts=10000),
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
    :param method: Function used to find balanced partitions at the 2-district level
        Defaults to :func:`~gerrychain.tree_methods.bipartition_tree`
    :type method: Callable, optional
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.bipartition_tree` to use.
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
        method=method,
        node_repeats=node_repeats,
        n=n,
        ceil=ceil,
    )
    for i in range(len(assignment)):
        for node in assignment[i]:
            flips[node] = parts[i]
    return flips


class BalanceError(Exception):
    """Raised when a balanced cut cannot be found."""


class PopulationBalanceError(Exception):
    """Raised when the population of a district is outside the acceptable epsilon range."""
