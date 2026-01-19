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
    Set,
    Union,
)

from ..graph import Graph
from .spanning_tree import random_spanning_tree

# frm: TODO: Documentation: Update the high level description for biparition_tree.py below

"""
This module implements algorithms for finding balanced subsets of nodes in a graph.

By "balanced" we mean that the total population in the subset is appropriate if the graph
were divided into N subsets of approximately the same size - where N is the number of districts
desired.

Stated differently, if you want to partition a graph into N equally sized subsets (by population)
of connected nodes, then this is the module that has those algorithms.

It leverages the GerryChain Graph object to handle graph structures.

Key functionalities include:

- The `_PopulatedGraph` class, which represents a graph with additional population data,
  and methods for assessing and modifying this data.
- Functions for finding balanced edge cuts in a populated graph, either through
  contraction or memoization techniques.
- The routines to find balanced subsets of nodes, such as bipartition_tree()

Dependencies:

- random: Provides random number generation for probabilistic approaches.
- typing: Used for type hints.

"""

"""
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
frm: TODO: Delete this comment after Peter does his part of the PR...

UPDATED PR COMMENT FOLLOWS:

I have substantially refactored this module.  This is what I have done:

Created a "tree" directory with an __init__.py and then created modules/files
below that.

Moved recursive_tree_part() and recursive_seed_part() into their own module

Moved espilon_tree_bipartition()

Unified the code that does the heavy lifting for biparition_tree().

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

    I also unified the many bipartition tree functions so that the use a
    new routine, internal_bipartition_tree(), which puts all of the logic
    in one place.  The differences between the externally visible bipartition
    tree functions are now trivial.

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

    All of the tests pass now.


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


# frm: Note to Peter - moved random_spanning_tree() to tree/spanning_tree.py

# frm: Note to Peter - moved uniform_spanning_tree() to tree/spanning_tree.py


# frm TODO: Documentation: _PopulatedGraph
#
# State what the purpose of this class is in the docstring comment below.
#
class _PopulatedGraph:
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
        ideal_pop: Union[int, float],
        epsilon: float,
    ) -> None:
        """
        :param graph: The underlying graph structure.
        :type graph: Graph
        :param populations: A dictionary mapping nodes to their populations.
        :type populations: Dict
        :param ideal_pop: The ideal population for each district.
        :type ideal_pop: Union[int, float]
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
        # new degree function could be replaced with just <_PopulatedGraph>.graph.degree(node_id)
        #
        # So unless there is a big performace gain (or some other reason), I would be
        # in favor of deleting the degree() method below and just using
        # <_PopulatedGraph>.graph.degree(node_id) on the assumption that both NX and RX
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
#        bipartition_tree_fn=partial(
#            bipartition_tree,
#            max_attempts=10000,
#            find_balanced_edge_cuts_fn=find_balanced_edge_cuts_contraction,
#
# and another in the same test file:
#
#    populated_tree = _PopulatedGraph(
#        tree, {node: 1 for node in tree}, len(tree) / 2, 0.5
#    )
#    cuts = find_balanced_edge_cuts_contraction(populated_tree)

# frm: TODO: Refactoring: params are find_balanced_edge_cuts_fn but routines are balanced_edge_...
#
# Another nit, but it would be nice if the parameter names were balanced_edge_fn (with a 'd'),
# but that is probably not possible given legacy code.
#
# Ask Peter to confirm that we should not change the name of either the param or the functions...
#
# Peter said (January 2026): I am fine with changing the name of that parameter.
# Python has good error messages for when things have the wrong name:
# and if users pass this as a positional argument, then it won't matter that the
# parameter name changed.


def find_balanced_edge_cuts_contraction(
    h: _PopulatedGraph, one_sided_cut: bool = False, root_choice_fn: Callable = random.choice
) -> List[Cut]:
    """
    Find balanced edge cuts using contraction.

    :param h: The populated graph.
    :type h: _PopulatedGraph
    :param one_sided_cut: Whether or not we are cutting off a single district. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param root_choice_fn: The function used to select the root node_id
    :type root_choice_fn: Callable, optional

    :returns: A list of balanced edge cuts.
    :rtype: List[Cut]
    """

    root = root_choice_fn([node_id for node_id in h.graph.node_indices if h.degree(node_id) > 1])
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
    :type h: _PopulatedGraph

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
    h: _PopulatedGraph, one_sided_cut: bool = False, root_choice_fn: Callable = random.choice
) -> List[Cut]:
    """
    Find balanced edge cuts using memoization.

    This function takes a _PopulatedGraph object and a choice function as input and returns a list
    of balanced edge cuts. A balanced edge cut is defined as a cut that divides the graph into
    two subsets, such that the population of each subset is close to the ideal population
    defined by the _PopulatedGraph object.

    :param h: The _PopulatedGraph object representing the graph.
    :type h: _PopulatedGraph
    :param one_sided_cut: Whether or not we are cutting off a single district. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param root_choice_fn: The choice function used to select the root node_id.
    :type root_choice_fn: Callable, optional

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

    root = root_choice_fn([node_id for node_id in h.graph.node_indices if h.degree(node_id) > 1])
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
        #
        # Peter said (January 2026):
        #
        # Ah, I have had this thought before, and I asked a student to look into it.
        # It is not unreasonable to be concerned that there might be topological
        # constraints in the graph that make some balanced edges "easier" to find
        # compared to others (the populations on the nodes make things really tricky
        # from a theory standpoint). If that is true, then picking the first edge
        # that you find can change the distribution that you are sampling from. I
        # conjecture that in regular (non-reversible) recom chains, the number of
        # spanning trees where such a distinction appears is sufficiently small
        # as to not bias the algorithm so long as the graph is not intentionally
        # made bad, but I am unaware of any proof. What work the student did seems
        # to lend credence to this conjecture as well, but the graphs they were able
        # to examine thoroughly were not sufficiently complicated as to justify a
        # change in the implementation.
        #
        # In addition, the published algorithm (Algorithm 6 here: https://mggg.org/uploads/ReCom.pdf)
        # samples uniformly # from the possible cut edges, so we should stick with that
        # until we have good reason to do otherwise.
        #
        # Also, the number of possible balance cut edges DOES matter for reversible
        # recom: it is a part of the formula that determines the acceptance probability
        # when doing approximate balance.

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
    populated_graph: _PopulatedGraph, region_surcharge: Dict, cut_edge_list: List[Cut]
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
    :type populated_graph: _PopulatedGraph
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

    # Check to see if the list of possible edge_cuts is one
    # with edge weights.  If not, then just select an edge at random.
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
#
# Peter said (January 2026): I think that this is fine. The sort of people
# that are mucking about with custom functions are also the sort of people
# that have time to devote to figuring out how to deal with the changes.
#
# And if they don't want to deal with RX, they can just pin to an old
# version of GerryChain or poke me for help

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
#      Peter replied: (January 2026): Uniform spanning trees sample
#      uniformly from the space of possible spanning trees, and minimum
#      spanning trees do NOT. So, you might modify things depending on
#      your target distribution.
#
#          => Add a comment saying that unless you have a very good
#             reason to prefer uniform_spanning_tree() then you should
#             probably just default to random_spanning_tree(), and then
#             list the reasons Peter has given in this and other comments.
#
#             For instance, he said this: MOST users want the minimum
#             spanning tree version. Some very specific researchers
#             (including my lab) want access to the uniform spanning
#             tree function for math reasons.
#
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
#       => Peter said (January 2026): Ah, I have wanted to do exactly this for a while.
#
#          The "one_sided_cut" thing was a hack that fixed a mathematical inaccuracy
#          in a previous version of GerryChain. As with most poor design choices,
#          this one was born of time pressure, and, since it was very, very unlikely
#          to be used by anyone that was not a developer in the lab, it has been left
#          in for far too long..
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


def internal_bipartition_tree(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    region_surcharge: Optional[Dict] = None,
    find_balanced_edge_cuts_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    root_choice_fn: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
    warn_attempts: int = 1000,
    allow_pair_reselection: bool = False,
    repeat_until_valid: bool = True,  # frm: TODO: Have this NOT default...
    cut_choice_fn: Callable = _region_preferred_max_weight_choice,
) -> Union[Set[Any], None]:

    # frm: TODO: Refactoring: Change the names of ALL function formal parameters to end
    #      in "_fn" - to make it clear that the paraemter is a function.  This will make it
    #      easier to do a global search to find all function parameters - as well as just being
    #      good coding practice...
    #
    # Peter said (January 2026): For the love of all that is good, please do. This
    # drives me nuts and a major release is a great place to make this sort of change
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
    :param find_balanced_edge_cuts_fn: The function to find balanced edge cuts. Defaults to
        :func:`find_balanced_edge_cuts_memoization`.
    :type find_balanced_edge_cuts_fn: Callable, optional
    :param one_sided_cut: Passed to the ``find_balanced_edge_cuts_fn``. Determines whether or not we are
        cutting off a single district when partitioning the tree. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param root_choice_fn: The function to make a random choice of root node for the population
        tree. Passed to ``find_balanced_edge_cuts_fn``. Can be substituted for testing.
        Defaults to :func:`random.random()`.
    :type root_choice_fn: Callable, optional
    :param max_attempts: The maximum number of attempts that should be made to bipartition.
        Defaults to 10000.
    :type max_attempts: Optional[int], optional
    :param warn_attempts: The number of attempts after which a warning is issued if a balanced
        cut cannot be found. Defaults to 1000.
    :type warn_attempts: int, optional
    :param allow_pair_reselection: Whether we would like to return an error to the calling
        function to ask it to reselect the pair of nodes to try and recombine. Defaults to False.
    :type allow_pair_reselection: bool, optional
    :param cut_choice_fn: The function used to select the cut edge from the list of possible
        balanced cuts. Defaults to :meth:`_region_preferred_max_weight_choice`. Note that
        this function should gracefully handle the case when the edges in the list of
        possible balanced cuts do not have edge weights - in this case, it should default
        to just random.random().
    :type cut_choice_fn: Callable, optional

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

    if "one_sided_cut" in signature(find_balanced_edge_cuts_fn).parameters:
        find_balanced_edge_cuts_fn = partial(
            find_balanced_edge_cuts_fn, one_sided_cut=one_sided_cut
        )

    # Find possible edge cuts if they exist.
    #
    # Note that _get_possible_edge_cuts_and_populated_graph() will raise and exception if max_attempts is exceeded.
    #
    cuts_and_populated_graph = _get_possible_edge_cuts_and_populated_graph(
        graph_to_split=subgraph_to_split,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        find_balanced_edge_cuts_fn=find_balanced_edge_cuts_fn,
        root_choice_fn=root_choice_fn,
        max_attempts=max_attempts,
        warn_attempts=warn_attempts,
        repeat_until_valid=repeat_until_valid,
        allow_pair_reselection=allow_pair_reselection,
    )
    possible_cuts = cuts_and_populated_graph[0]
    populated_graph = cuts_and_populated_graph[1]

    # frm: TODO: Refactoring:  Think about whether we should pass warn_attempts to
    # other calls on _get_possible_edge_cuts_and_populated_graph()
    #
    # Peter said (January 2026): Honestly, we should just change a bunch of
    # these warnings into logging statements and tell users to modify the log level
    # if they want to figure out what went wrong.
    #
    # Logging is another thing on the list, but the refactor is more important to do first

    num_cuts = len(possible_cuts)
    if num_cuts != 0:

        # frm: TODO: ???:  Is it an error to pass in a None value for region_surcharge,
        #                  but to also pass a cut_choice_fn function that expects a region_surcharge?

        is_region_cut = (
            "region_surcharge" in signature(cut_choice_fn).parameters
            and "populated_graph" in signature(cut_choice_fn).parameters
        )

        if is_region_cut:
            chosen_cut = cut_choice_fn(populated_graph, region_surcharge, possible_cuts)
        else:
            chosen_cut = cut_choice_fn(possible_cuts)

        parent_node_ids = subgraph_to_split.translate_subgraph_node_ids_for_set_of_nodes(
            chosen_cut.subset
        )
        # frm: Not sure if it is important that the returned set be a frozenset...
        return num_cuts, frozenset(parent_node_ids)

    else:
        # No balanced edge_cuts were found.
        #
        # This is OK if the repeat_until_valid flag is False.  In that case (which is
        # related to reversible_recom()) we should return 0 for num_cuts and an
        # empty list of node_ids.  This will signal to the caller that we failed to
        # find any balanced edge_cuts.
        #
        # However, if repeat_until_valid is True, then an exception will be raised by
        # lower level code, so we should never end up in the else-part of this if-stmt.
        # One might argue that using exceptions this way is not quite cool, but that
        # is the way this code works...
        #
        if not repeat_until_valid:
            empty_set = set()
            return 0, empty_set
        else:
            # frm: TODO: Refactoring: Clean this up...
            raise Exception("This should never happen...")


# frm: TODO: Refactoring: Delete old_bipartion_tree() after Peter has done PR
#
# Note to Peter:  I am including this code so that you can have it at hand to
# see what used to happen before I unified the logic for all of the
# different bipartition_tree functions.
#
# As you will see bipartition_tree() now just calls internal_bipartition_tree()
# which does the real work, with the help of _get_possible_edge_cuts_and_populated_graph().


def old_bipartition_tree(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    region_surcharge: Optional[Dict] = None,
    find_balanced_edge_cuts_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    root_choice_fn: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
    warn_attempts: int = 1000,
    allow_pair_reselection: bool = False,
    cut_choice_fn: Callable = _region_preferred_max_weight_choice,
) -> Set:
    # frm: TODO: Refactoring: Change the names of ALL function formal parameters to end
    #      in "_fn" - to make it clear that the paraemter is a function.  This will make it
    #      easier to do a global search to find all function parameters - as well as just being
    #      good coding practice...
    #
    # Peter said (January 2026): For the love of all that is good, please do. This
    # drives me nuts and a major release is a great place to make this sort of change
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
    :param find_balanced_edge_cuts_fn: The function to find balanced edge cuts. Defaults to
        :func:`find_balanced_edge_cuts_memoization`.
    :type find_balanced_edge_cuts_fn: Callable, optional
    :param one_sided_cut: Passed to the ``find_balanced_edge_cuts_fn``. Determines whether or not we are
        cutting off a single district when partitioning the tree. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param root_choice_fn: The function to make a random choice of root node for the population
        tree. Passed to ``find_balanced_edge_cuts_fn``. Can be substituted for testing.
        Defaults to :func:`random.random()`.
    :type root_choice_fn: Callable, optional
    :param max_attempts: The maximum number of attempts that should be made to bipartition.
        Defaults to 10000.
    :type max_attempts: Optional[int], optional
    :param warn_attempts: The number of attempts after which a warning is issued if a balanced
        cut cannot be found. Defaults to 1000.
    :type warn_attempts: int, optional
    :param allow_pair_reselection: Whether we would like to return an error to the calling
        function to ask it to reselect the pair of nodes to try and recombine. Defaults to False.
    :type allow_pair_reselection: bool, optional
    :param cut_choice_fn: The function used to select the cut edge from the list of possible
        balanced cuts. Defaults to :meth:`_region_preferred_max_weight_choice`. Note that
        this function should gracefully handle the case when the edges in the list of
        possible balanced cuts do not have edge weights - in this case, it should default
        to just random.random().
    :type cut_choice_fn: Callable, optional

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

    if "one_sided_cut" in signature(find_balanced_edge_cuts_fn).parameters:
        find_balanced_edge_cuts_fn = partial(
            find_balanced_edge_cuts_fn, one_sided_cut=one_sided_cut
        )

    # Find possible edge cuts if they exist.
    #
    # Note that _get_possible_edge_cuts_and_populated_graph() will raise and exception if max_attempts is exceeded.
    #
    cuts_and_populated_graph = _get_possible_edge_cuts_and_populated_graph(
        graph_to_split=subgraph_to_split,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        find_balanced_edge_cuts_fn=find_balanced_edge_cuts_fn,
        root_choice_fn=root_choice_fn,
        max_attempts=max_attempts,
        warn_attempts=warn_attempts,
        repeat_until_valid=True,
        allow_pair_reselection=allow_pair_reselection,
    )
    possible_cuts = cuts_and_populated_graph[0]
    populated_graph = cuts_and_populated_graph[1]

    # frm: TODO: Refactoring:  Think about whether we should pass warn_attempts to
    # other calls on _get_possible_edge_cuts_and_populated_graph()
    #
    # Peter said (January 2026): Honestly, we should just change a bunch of
    # these warnings into logging statements and tell users to modify the log level
    # if they want to figure out what went wrong.
    #
    # Logging is another thing on the list, but the refactor is more important to do first

    num_cuts = len(possible_cuts)
    if num_cuts != 0:

        # frm: TODO: ???:  Is it an error to pass in a None value for region_surcharge,
        #                  but to also pass a cut_choice_fn function that expects a region_surcharge?

        is_region_cut = (
            "region_surcharge" in signature(cut_choice_fn).parameters
            and "populated_graph" in signature(cut_choice_fn).parameters
        )

        chosen_cut = None
        if is_region_cut:
            chosen_cut = cut_choice_fn(populated_graph, region_surcharge, possible_cuts)
        else:
            chosen_cut = cut_choice_fn(possible_cuts)

        parent_node_ids = subgraph_to_split.translate_subgraph_node_ids_for_set_of_nodes(
            chosen_cut.subset
        )
        # frm: Not sure if it is important that the returned set be a frozenset...
        return frozenset(parent_node_ids)

    else:
        # frm: TODO: Refactoring: Clean this up...
        raise Exception("This should never happen...")

        # frm: TODO: Refactoring:  Have all versions of cut_choice_fn have same signatures.
        #
        # Better approach is to have all of the poosible paramters exist
        # in ALL of the versions of the cut_choice_fn() functions and to
        # have them default to None if not used by one of the functions.
        # Then this code could just pass in the values to the
        # cut_choice_fn function, and it could make sense of what to do.
        #
        # This makes it clear what the overall and comprehensive purpose
        # of cut_choice_fn functions are.  This centralizes the knowlege
        # of what a cut_choice_fn() function is supposed to do - or at least
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


def bipartition_tree(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    region_surcharge: Optional[Dict] = None,
    find_balanced_edge_cuts_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    root_choice_fn: Callable = random.choice,
    repeat_until_valid: bool = True,
    max_attempts: Optional[int] = 100000,
    warn_attempts: int = 1000,
    allow_pair_reselection: bool = False,
    cut_choice_fn: Callable = _region_preferred_max_weight_choice,
) -> Set:
    # frm: TODO: Refactoring: Change the names of ALL function formal parameters to end
    #      in "_fn" - to make it clear that the paraemter is a function.  This will make it
    #      easier to do a global search to find all function parameters - as well as just being
    #      good coding practice...
    #
    # Peter said (January 2026): For the love of all that is good, please do. This
    # drives me nuts and a major release is a great place to make this sort of change
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
    :param find_balanced_edge_cuts_fn: The function to find balanced edge cuts. Defaults to
        :func:`find_balanced_edge_cuts_memoization`.
    :type find_balanced_edge_cuts_fn: Callable, optional
    :param one_sided_cut: Passed to the ``find_balanced_edge_cuts_fn``. Determines whether or not we are
        cutting off a single district when partitioning the tree. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param root_choice_fn: The function to make a random choice of root node for the population
        tree. Passed to ``find_balanced_edge_cuts_fn``. Can be substituted for testing.
        Defaults to :func:`random.random()`.
    :type root_choice_fn: Callable, optional
    :param max_attempts: The maximum number of attempts that should be made to bipartition.
        Defaults to 10000.
    :type max_attempts: Optional[int], optional
    :param warn_attempts: The number of attempts after which a warning is issued if a balanced
        cut cannot be found. Defaults to 1000.
    :type warn_attempts: int, optional
    :param allow_pair_reselection: Whether we would like to return an error to the calling
        function to ask it to reselect the pair of nodes to try and recombine. Defaults to False.
    :type allow_pair_reselection: bool, optional
    :param cut_choice_fn: The function used to select the cut edge from the list of possible
        balanced cuts. Defaults to :meth:`_region_preferred_max_weight_choice`. Note that
        this function should gracefully handle the case when the edges in the list of
        possible balanced cuts do not have edge weights - in this case, it should default
        to just random.random().
    :type cut_choice_fn: Callable, optional

    :returns: A subset of nodes of ``graph`` (whose induced subgraph is connected). The other
        part of the partition is the complement of this subset.
    :rtype: Set

    :raises BipartitionWarning: If a possible cut cannot be found after 1000 attempts.
    :raises RuntimeError: If a possible cut cannot be found after the maximum number of attempts
        given by ``max_attempts``.
    """
    num_cuts, node_ids = internal_bipartition_tree(
        subgraph_to_split=subgraph_to_split,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        region_surcharge=region_surcharge,
        find_balanced_edge_cuts_fn=find_balanced_edge_cuts_fn,
        one_sided_cut=one_sided_cut,
        root_choice_fn=root_choice_fn,
        max_attempts=max_attempts,
        warn_attempts=warn_attempts,
        allow_pair_reselection=allow_pair_reselection,
        repeat_until_valid=repeat_until_valid,
        cut_choice_fn=cut_choice_fn,
    )

    # Note that the value of repeat_until_valid in the above call controls
    # whether node_ids is allowed to be the empty_set.
    #
    # Typically, repeat_until_valid is set to True (usually by default) which
    # tells the internal_bipartition_tree() function to keep trying to find
    # balanced edge cuts until it reaches max_attempt, at which point it
    # raises an exception (hence no node_ids returned at all).
    #
    # However, if repeat_until_valid is set to False (which is done for
    # reversible_recom(), then internal_bipartition_tree() will NOT loop
    # and it will just return whatever it finds for balanced edge cuts
    # after the first attempt, in which case node_ids can be the empty set).

    return node_ids

    # frm: TODO: Refactoring:  Again - we should NOT be changing semantics based
    #                   on the names in signatures...
    # Better approach is to have all of the poosible paramters exist
    # in ALL of the versions of the cut_choice_fn() functions and to
    # have them default to None if not used by one of the functions.
    # Then this code could just pass in the values to the
    # cut_choice_fn function, and it could make sense of what to do.
    #
    # This makes it clear what the overall and comprehensive purpose
    # of cut_choice_fn functions are.  This centralizes the knowlege
    # of what a cut_choice_fn() function is supposed to do - or at least
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


# frm: TODO: Refactoring: should _get_possible...() have default values for params?
#
# It is an internal routine that is called by routines that should know exactly
# what they want, so I am inclined to remove ALL of the default parameter values...


def _get_possible_edge_cuts_and_populated_graph(
    #
    # Note: Complexity Alert...  _get_possible_edge_cuts_and_populated_graph does NOT translate
    # node_ids to parent graph context.  The reason is that if there are several possible
    # edge_cuts found, it is not yet clear which of the edge_cuts to actually cut, and hence
    # which node_ids to translate, so we leave both the selection of which edge_cut to cut and
    # the translation of node_ids to the caller.
    #
    graph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    find_balanced_edge_cuts_fn: Callable = find_balanced_edge_cuts_memoization,
    root_choice_fn: Callable = random.choice,
    repeat_until_valid: bool = True,
    warn_attempts: int = 1000,
    max_attempts: Optional[int] = 100000,
    allow_pair_reselection: bool = False,
) -> tuple[List[Cut], _PopulatedGraph]:
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
    :param find_balanced_edge_cuts_fn: The function to find balanced edge cuts. Defaults to
        find_balanced_edge_cuts_memoization.
    :type find_balanced_edge_cuts_fn: Callable, optional
    :param root_choice_fn: The function to choose a random element from a list. Defaults to random.choice.
    :type root_choice_fn: Callable, optional
    :param max_attempts: The maximum number of attempts to find a valid bipartition. If None,
        there is no limit. Defaults to None.
    :type max_attempts: Optional[int], optional

    :returns: A tuple with a list of possible cuts that bipartition the tree into two subgraphs and
        the _PopulatedGraph the cuts were obtained from.
    :rtype: tuple[List[tuple[Hashable, Hashable]], _PopulatedGraph]

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
    #
    # Peter agreed (January 2026) - he said we should force it to be an int and put a defensive
    # check before this...

    while max_attempts is None or attempts < max_attempts:
        if restarts == node_repeats:
            spanning_tree = spanning_tree_fn(graph_to_split)
            restarts = 0
        h = _PopulatedGraph(spanning_tree, populations, pop_target, epsilon)
        possible_cuts = find_balanced_edge_cuts_fn(
            h, root_choice_fn=root_choice_fn
        )  # a list of cuts

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
        num_cuts = len(possible_cuts)
        if num_cuts != 0:
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


# frm: TODO: Refactoring: Delete old_bipartion_tree_random_with_num_cuts() after Peter has done PR
#
# Note to Peter:  I am including this code so that you can have it at hand to
# see what used to happen before I unified the logic for all of the
# different bipartition_tree functions.
#
# As you will see bipartition_tree_random_with_num_cuts() now just calls internal_bipartition_tree()
# which does the real work, with the help of _get_possible_edge_cuts_and_populated_graph().


def old_bipartition_tree_random_with_num_cuts(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    repeat_until_valid: bool = True,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    find_balanced_edge_cuts_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    root_choice_fn: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
    cut_choice_fn: Callable = random.choice,
) -> tuple[int, Set[Any]]:
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
    :param find_balanced_edge_cuts_fn: The algorithm used to find balanced cut edges. Defaults to
        :func:`find_balanced_edge_cuts_memoization`.
    :type find_balanced_edge_cuts_fn: Callable, optional
    :param one_sided_cut: Passed to the ``find_balanced_edge_cuts_fn``. Determines whether or not we are
        cutting off a single district when partitioning the tree. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param root_choice_fn: The random choice function. Can be substituted for testing. Defaults
        to :func:`random.choice`.
    :type root_choice_fn: Callable, optional
    :param max_attempts: The max number of attempts that should be made to bipartition.
        Defaults to None.
    :type max_attempts: Optional[int], optional
    :param cut_choice_fn: The function to use to select which cut to use if there are more than one.
        It defaults to random.choice()
    :type cut_choice_fn: Callable, optional

    :returns: A subset of nodes of ``graph`` (whose induced subgraph is connected) or None if a
        valid spanning tree is not found.
    :rtype: tuple[int, Set[Any]]
    """

    # frm: TODO: Refactoring:  Again - semantics should not depend on signatures...
    if "one_sided_cut" in signature(find_balanced_edge_cuts_fn).parameters:
        find_balanced_edge_cuts_fn = partial(find_balanced_edge_cuts_fn, one_sided_cut=True)

    cuts_and_populated_graph = _get_possible_edge_cuts_and_populated_graph(
        graph_to_split=subgraph_to_split,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        repeat_until_valid=repeat_until_valid,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        find_balanced_edge_cuts_fn=find_balanced_edge_cuts_fn,
        root_choice_fn=root_choice_fn,
        max_attempts=max_attempts,
    )
    possible_cuts = cuts_and_populated_graph[0]

    num_cuts = len(possible_cuts)
    if num_cuts != 0:
        # frm: TODO: Refactoring: this should be choice_cut not root_choice_fn()
        chosen_cut = root_choice_fn(possible_cuts)
        parent_node_ids = subgraph_to_split.translate_subgraph_node_ids_for_set_of_nodes(
            chosen_cut.subset
        )
        return num_cuts, frozenset(
            parent_node_ids
        )  # frm: Not sure if important that it be frozenset
    else:
        empty_set = set()
        return 0, empty_set


# frm: TODO: Refactoring: Verify with Peter that this is NOT part of the external API.
#
# It is used for reversible_recom() where repeat_until_valid is set to False, so that
# it stops after one attempt to find balanced edge_cuts.
#
# It is also used in this routine as the implementation of bipartition_tree_random(),
# but bipartition_tree_random is effectively never used, so I am hoping to just
# delete it too.
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
    find_balanced_edge_cuts_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    root_choice_fn: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
    cut_choice_fn: Callable = random.choice,
) -> tuple[int, Set[Any]]:
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
    :param find_balanced_edge_cuts_fn: The algorithm used to find balanced cut edges. Defaults to
        :func:`find_balanced_edge_cuts_memoization`.
    :type find_balanced_edge_cuts_fn: Callable, optional
    :param one_sided_cut: Passed to the ``find_balanced_edge_cuts_fn``. Determines whether or not we are
        cutting off a single district when partitioning the tree. When
        set to False, we check if the node we are cutting and the remaining graph
        are both within epsilon of the ideal population. When set to True, we only
        check if the node we are cutting is within epsilon of the ideal population.
        Defaults to False.
    :type one_sided_cut: bool, optional
    :param root_choice_fn: The random choice function. Can be substituted for testing. Defaults
        to :func:`random.choice`.
    :type root_choice_fn: Callable, optional
    :param max_attempts: The max number of attempts that should be made to bipartition.
        Defaults to None.
    :type max_attempts: Optional[int], optional
    :param cut_choice_fn: The function to use to select which cut to use if there are more than one.
        It defaults to random.choice()
    :type cut_choice_fn: Callable, optional

    :returns: A subset of nodes of ``graph`` (whose induced subgraph is connected) or None if a
        valid spanning tree is not found.
    :rtype: tuple[int, Set[Any]]
    """

    num_cuts, node_ids = internal_bipartition_tree(
        subgraph_to_split=subgraph_to_split,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        # region_surcharge: Optional[Dict] = None,
        find_balanced_edge_cuts_fn=find_balanced_edge_cuts_fn,
        one_sided_cut=one_sided_cut,
        root_choice_fn=root_choice_fn,
        max_attempts=max_attempts,
        # warn_attempts: int = 1000,
        # allow_pair_reselection: bool = False,
        repeat_until_valid=repeat_until_valid,
        cut_choice_fn=cut_choice_fn,
    )

    return num_cuts, node_ids

    # frm: TODO: Refactoring: Should it be an error if warn_attempts > max_attempts?


#######################


# frm: TODO: Refactoring: Delete bipartition_tree_random()
#
# As far as I can tell, this is a relic of the past.  It is only ever referred to in
# _get_seed_chunks() and in the constructor for the class ReCom (which I think is never
# used and is itself a relic that should be deleted).  I think that _get_seed_chunks
# will work just fine with bipartition_tree() instead of bipartition_tree_random()
# at which point we can just delete bipartition_tree_random().
#
#    *sigh*
#
# OK - after a good bit of head scratching, I convinced myself that bipartition_tree_random()
# was actuall EXACTLY the same as bipartition_tree() after I added repeat_until_valid to
# the signature of bipartition_tree() - defaulting it to True.
#
# So the implementation of bipartition_tree_random() is now just a call on bipartition_tree().
#
# Once Peter approves, I will delete this.
#
# This should be added to the release notes just in case someone in the wide world uses it.


def bipartition_tree_random(
    subgraph_to_split: Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    repeat_until_valid: bool = True,
    spanning_tree: Optional[Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    find_balanced_edge_cuts_fn: Callable = find_balanced_edge_cuts_memoization,
    one_sided_cut: bool = False,
    root_choice_fn: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
    cut_choice_fn: Callable = random.choice,
) -> Union[Set[Any], None]:
    """
    This routine is deprecated - use bipartition_tree() instead
    """

    # bipartition_tree_random_with_num_cuts() does what we want and more.
    # so call it and then just disregard the num_cuts, which we don't care about
    # in this case...
    #

    return bipartition_tree(
        subgraph_to_split=subgraph_to_split,
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        spanning_tree=spanning_tree,
        spanning_tree_fn=spanning_tree_fn,
        # region_surcharge: Optional[Dict] = None,
        find_balanced_edge_cuts_fn=find_balanced_edge_cuts_fn,
        one_sided_cut=one_sided_cut,
        root_choice_fn=root_choice_fn,
        max_attempts=max_attempts,
        # warn_attempts: int = 1000,
        # allow_pair_reselection: bool = False,
        repeat_until_valid=repeat_until_valid,
        cut_choice_fn=cut_choice_fn,
    )


class BalanceError(Exception):
    """Raised when a balanced cut cannot be found."""


class PopulationBalanceError(Exception):
    """Raised when the population of a district is outside the acceptable epsilon range."""


# frm: TODO: Delete these notes to Peter after next PR:

# Note to Peter:  param name, "method", has been changed everywhere to "bipartition_tree_fn"
#
# I have added a note to the rx_release_notes.md file that we should warn users about this
# change.

# frm: Note to Peter:  I moved the defintion of epsilon_tree_bipartition() to tree_proposals.py
#
# I also had to import the two exceptions BalanceError and PopulationBalanceError into
# tree_proposals.py.  I felt funny about doing so, but it didn't seem terrible...

# frm: Note to Peter - moved recursive_seed_part() to partition/initial_partition_generators.py

# frm: Note to Peter - moved _get_seed_chunks() to partition/initial_partition_generators.py

# frm: Note to Peter - moved get_max_prime_factor_less_than() to partition/initial_partition_generators.py

# frm: Note to Peter - moved _recursive_seed_part_inner() to partition/initial_partition_generators.py

# frm: Note to Peter - moved _recursive_seed_part_inner() to partition/initial_partition_generators.py

# frm: Note to Peter - moved _recursive_seed_part_inner() to partition/initial_partition_generators.py
