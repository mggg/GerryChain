"""
This module provides tools and algorithms for manipulating and analyzing graphs,
particularly focused on partitioning graphs based on population data. It leverages the
NetworkX library to handle graph structures and implements various algorithms for graph
partitioning and tree traversal.

Key functionalities include:

- Predecessor and successor functions for graph traversal using breadth-first search.
- Implementation of random and uniform spanning trees for graph partitioning.
- The `PopulatedGraph` class, which represents a graph with additional population data,
  and methods for assessing and modifying this data.
- Functions for finding balanced edge cuts in a populated graph, either through
  contraction or memoization techniques.
- A suite of functions (`bipartition_tree`, `recursive_tree_part`, `_get_seed_chunks`, etc.)
  for partitioning graphs into balanced subsets based on population targets and tolerances.
- Utility functions like `get_max_prime_factor_less_than` and `recursive_seed_part_inner`
  to assist in complex partitioning tasks.

Dependencies:

- networkx: Used for graph data structure and algorithms.
- random: Provides random number generation for probabilistic approaches.
- typing: Used for type hints.

Last Updated: 25 April 2024
"""
# frm:  This file, tree.py, needed to be modified to operate on new Graph
#       objects instead of NetworkX Graph objects because the routines are
#       used by the Graph objects inside a Partion, which will soon be based
#       on RustworkX.  More specifically, these routines are used by Proposals,
#       and we will soon switch to having the underlying Graph object used
#       in Partitions and Proposals be based on RustworkX.
#
#       It may be the case that they are ONLY ever used by Proposals and 
#       hence could just have been rewritten to operate on RustworkX Graph
#       objects, but there seemed to be no harm in having them work either 
#       way.  It was also a good proving ground for testing whether the new
#       Graph object could behave like a NetworkX Graph object (in terms of
#       attribute access and syntax).

"""
frm: RX Documentation

Many of the functions in this file operate on subgraphs which are different from
NX subgraphs because the node_ids change in the subgraph.  To deal with this, 
in graph.py we have a _node_id_to_parent_node_id_map data member for Graph objects which maps
the node_ids in a subgraph to the corresponding node_id in its parent graph.  This
will allow routines operating on subgraphs to return results using the node_ids
of the parent graph.

Note that for top-level graphs, we still define this _node_id_to_parent_node_id_map, but in
this case it is an identity map that just maps each node_id to itself.  This allows
code to always translate correctly, even if operating on a top-level graph.

As a matter of coding convention, all calls to graph.subgraph() have been placed
in the actual parameter list of function calls.  This limits the scope of the
subgraph node_ids to the called function - eliminating the risk of those node_ids
leaking into surrounding code.  Stated differently, this eliminates the cognitive
load of trying to remember whether a node_id is a parent or a subgraph node_id.
"""

import networkx as nx
import rustworkx as rx
import numpy as np
from scipy.sparse import csr_array
# frm TODO:     Remove import of networkx and rustworkx once we have moved networkx
#               dependencies out of this file - see comments below on 
#               spanning trees.

import networkx.algorithms.tree as nxtree
# frm TODO:     Remove import of "tree" from networkx.algorithms in this file
#               It is only used to get a spanning tree function:
#
#                   spanning_tree = nxtree.minimum_spanning_tree(
#
#               There is an RX function that also computes a spanning tree - hopefully
#               it works as we want it to work and hence can be used.
#
#               I think it probably makes sense to move this spanning tree function
#               into graph.py and to encapsulate the NX vs RX code there.
#
# Note Peter agrees with this...

from functools import partial
from inspect import signature
import random
from collections import deque, namedtuple
import itertools
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Union,
    Hashable,
    Sequence,
    Tuple,
)
import warnings

# frm:  import the new Graph object which encapsulates NX and RX Graph...
from .graph import Graph

# frm TODO: Update function param docmentation to get rid of nx.Graph and use just Graph

def random_spanning_tree(
    graph: Graph,              # frm: Original code:    graph: x.Graph, 
    region_surcharge: Optional[Dict] = None
) -> Graph:                # frm: Original code:      ) -> nx.Graph:
    """
    Builds a spanning tree chosen by Kruskal's method using random weights.

    :param graph: The input graph to build the spanning tree from. Should be a Networkx Graph.
    :type graph: nx.Graph
    :param region_surcharge: Dictionary of surcharges to add to the random
        weights used in region-aware variants.
    :type region_surcharge: Optional[Dict], optional

    :returns: The maximal spanning tree represented as a Networkx Graph.
    :rtype: nx.Graph
    """
    # frm: ???:
    #           This seems to me to be an expensive way to build a random spanning
    #           tree.  It calls a routine to compute a "minimal" spanning tree that
    #           computes the total "weight" of the spanning tree and selects the 
    #           minmal total weight.  By making the weights random, this will select
    #           a different spanning tree each time.  This works, but it does not
    #           in any way depend on the optimization.  
    #
    #           Why isn't the uniform_spanning_tree() below adequate?  It takes
    #           a random walk at each point to create the spanning tree.  This 
    #           would seem to be a much cheaper way to calculate a spanning tree.
    #
    #           What am I missing???

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

    # frm: TODO:  WTF is up with region_surcharge being unset?  The region_surcharge
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
    #     def random_spanning_tree(
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

    # frm: Original Code:   for edge in graph.edges():
    #       Changed because in RX edge_ids are integers while edges are tuples

    for edge_id in graph.edge_indices:
        edge = graph.get_edge_from_edge_id(edge_id)
        weight = random.random()
        for key, value in region_surcharge.items():
            # We surcharge edges that cross regions and those that are not in any region
            if (
                # frm: original code:   graph.nodes[edge[0]][key] != graph.nodes[edge[1]][key]
                # frm: original code:   or graph.nodes[edge[0]][key] is None
                # frm: original code:   or graph.nodes[edge[1]][key] is None
                graph.node_data(edge[0])[key] != graph.node_data(edge[1])[key]
                or graph.node_data(edge[0])[key] is None
                or graph.node_data(edge[1])[key] is None
            ):
                weight += value

        # frm: Original Code:    graph.edges[edge]["random_weight"] = weight
        graph.edge_data(edge_id)["random_weight"] = weight

    # frm: CROCK: (for the moment)
    #               We need to create a minimum spanning tree but the way to do so
    #               is different for NX and RX.  I am sure that there is a more elegant
    #               way to do this, and in any event, this dependence on NX vs RX 
    #               should not be in this file, tree.py, but for now, I am just trying
    #               to get this to work, so I am using CROCKS...

    graph.verify_graph_is_valid()

    # frm: TODO:  Remove NX / RX dependency - maybe move to graph.py

    if (graph.is_nx_graph()):
        nx_graph = graph.get_nx_graph()
        spanning_tree = nxtree.minimum_spanning_tree(
            nx_graph, algorithm="kruskal", weight="random_weight"
        )
        spanningGraph = Graph.from_networkx(spanning_tree)
    elif (graph.is_rx_graph()):
        rx_graph = graph.get_rx_graph()
        def get_weight(edge_data):
            # function to get the weight of an edge from its data
            # This function is passed a dict with the data for the edge.
            return edge_data["random_weight"]
        spanning_tree = rx.minimum_spanning_tree(rx_graph, get_weight)
        spanningGraph = Graph.from_rustworkx(spanning_tree)
    else:
        raise Exception("random_spanning_tree - bad kind of graph object")

    return spanningGraph

def uniform_spanning_tree(
    # frm: Original code:    graph: nx.Graph, choice: Callable = random.choice
    graph: Graph,          
    choice: Callable = random.choice
) -> Graph:
    """
    Builds a spanning tree chosen uniformly from the space of all
    spanning trees of the graph. Uses Wilson's algorithm.

    :param graph: Networkx Graph
    :type graph: nx.Graph
    :param choice: :func:`random.choice`. Defaults to :func:`random.choice`.
    :type choice: Callable, optional

    :returns: A spanning tree of the graph chosen uniformly at random.
    :rtype: nx.Graph
    """
    
    """
    frm: RX Docmentation:
    
    As with random_spanning_tree, I am assuming that the issue of RX subgraphs having 
    different node_ids is not an issue for this routine...
    """
    # Pick a starting point at random
    root_id = choice(list(graph.node_indices))
    tree_nodes = set([root_id])
    next_node_id = {root_id: None}

    # frm: I think that this builds a tree bottom up.  It takes
    #       every node in the graph (in sequence).  If the node
    #       is already in the list of nodes that have been seen
    #       which means it has a neighbor registered as a next_node,
    #       then it is skipped.  If this node does not yet have
    #       a neighbor registered, then it is given one, and 
    #       that neighbor becomes the next node looked at.
    #       
    #       This essentially takes a node and travels "up" until
    #       it finds a node that is already in the tree.  Multiple
    #       nodes can end up with the same "next_node" - which
    #       in tree-speak means that next_node is the parent of
    #       all of the nodes that end on it.
           
    for node_id in graph.node_indices:
        u = node_id
        while u not in tree_nodes:
            next_node_id[u] = choice(list(graph.neighbors(u)))
            u = next_node_id[u]

        u = node_id
        while u not in tree_nodes:
            tree_nodes.add(u)
            u = next_node_id[u]

    # frm DONE:  To support RX, I added an add_edge() method to Graph. 

    # frm: TODO:  Remove dependency on NX below

    # frm: Original code:    G = nx.Graph()  
    nx_graph = nx.Graph()
    G = Graph.from_networkx(nx_graph)

    for node_id in tree_nodes:
        if next_node_id[node_id] is not None:
            G.add_edge(node_id, next_node_id[node_id])

    return G


# frm TODO  
#
#               I think that this is only ever used inside this module (except)
#               for testing.
#
class PopulatedGraph:
    """
    A class representing a graph with population information.

    :ivar graph: The underlying graph structure.
    :type graph: nx.Graph
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
        graph: Graph,         # frm: Original code:    graph: nx.Graph,
        populations: Dict,
        ideal_pop: Union[float, int],
        epsilon: float,
    ) -> None:
        """
        :param graph: The underlying graph structure.
        :type graph: nx.Graph
        :param populations: A dictionary mapping nodes to their populations.
        :type populations: Dict
        :param ideal_pop: The ideal population for each district.
        :type ideal_pop: Union[float, int]
        :param epsilon: The tolerance for population deviation as a percentage of
            the ideal population within each district.
        :type epsilon: float
        """
        self.graph = graph
        self.subsets = {node: {node} for node in graph.nodes}
        self.population = populations.copy()
        self.tot_pop = sum(self.population.values())
        self.ideal_pop = ideal_pop
        self.epsilon = epsilon
        self._degrees = {node: graph.degree(node) for node in graph.nodes}

    # frm TODO:  Verify that this does the right thing for the new Graph object
    def __iter__(self):
        return iter(self.graph)

    def degree(self, node) -> int:
        return self._degrees[node]

    # frm: only ever used inside this file
    #       But maybe this is intended to be used externally...
    #
    # In PR: Peter said:
    #
    # We do use this external to the class when calling find_balance_edge_cuts_contraction


    # frm: ???: What the fat does this do?  Start with what a population is.  It 
    #           appears to be indexed by node.  Also, what is a subset?  GRRRR...
    def contract_node(self, node, parent) -> None:
        # frm: ???: TODO:  This routine is only used once, so why have a separate
        #                   routine - why not just include this code inline where
        #                   the function is now called?  It would be simpler to read
        #                   inline than having to go find this definition.
        #
        #                   Perhaps it is of use externally, but that seems doubtful...

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
        
        # frm: ???: TODO:  this logic is repeated several times in this file.  Consider
        #                   refactoring the code so that the logic lives in exactly
        #                   one place.
        #
        #                   When thinking about refactoring, consider whether it makes
        #                   sense to toggle what this routine does by the "one_sided_cut"
        #                   parameter.  Why not have two separate routines with 
        #                   similar but distinguishing names.  I need to be absolutely
        #                   clear about what the two cases are all about, but my current
        #                   hypothesis is that when one_sided_cut == False, we are looking
        #                   for the edge which when cut produces two districts of 
        #                   approximately equal size - so a bisect rather than a find all
        #                   meaning...

        if one_sided_cut:
            return (
                abs(self.population[node] - self.ideal_pop)
                < self.epsilon * self.ideal_pop
            )

        return (
            abs(self.population[node] - self.ideal_pop) <= self.epsilon * self.ideal_pop
            and abs((self.tot_pop - self.population[node]) - self.ideal_pop)
            <= self.epsilon * self.ideal_pop
        )

    def __repr__(self) -> str:
        graph_info = (
            f"Graph(nodes={len(self.graph.nodes)}, edges={len(self.graph.edges)})"
        )
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
Cut.subset.__doc__ = (
    "The (frozen) subset of nodes on one side of the cut. Defaults to None."
)

# frm: TODO:  Not sure how this is used, and so I do not know whether it needs
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

    root = choice([x for x in h if h.degree(x) > 1])
    # BFS predecessors for iteratively contracting leaves
    # frm: Original code:      pred = predecessors(h.graph, root)
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

    leaves = deque(x for x in h if h.degree(x) == 1)
    while len(leaves) > 0:
        leaf = leaves.popleft()
        if h.has_ideal_population(leaf, one_sided_cut=one_sided_cut):
            # frm: If the population of the subtree rooted in this node is the correct
            #       size, then add it to the cut list.  Note that if one_sided_cut == False,
            #       then the cut means the cut bisects the partition (frm: ??? need to verify this).
            e = (leaf, pred[leaf])
            cuts.append(
                Cut(
                    edge=e,
                    # frm: Original Code:  weight=h.graph.edges[e].get("random_weight", random.random()),
                    # frm: TODO: edges vs. edge_ids:  edge_ids are wanted here (integers)
                    weight=h.graph.edge_data(
                        h.graph.get_edge_id_from_edge(e)
                    ).get("random_weight", random.random()),
                    subset=frozenset(h.subsets[leaf].copy()),
                )
            )
        # Contract the leaf:  frm: merge the leaf's population into the parent and add the parent to "leaves"
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

    frm: ???: TODO:  Rename this to be more descriptive - perhaps ]
                     something like: _nodes_in_subtree() or
                     _nodes_for_cut()
    
    frm: TODO:  Add the above explanation for what a Cut is and how
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

#frm: used externally by tree_proposals.py
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

    root = choice([x for x in h if h.degree(x) > 1])
    # frm: Original code:   pred = predecessors(h.graph, root)
    # frm: Original code:   succ = successors(h.graph, root)
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
                        # frm: Original Code:   weight=h.graph.edges[e].get("random_weight", wt),
                        # frm: edges vs. edge_ids:  edge_ids are wanted here (integers)
                        weight=h.graph.edge_data(
                            h.graph.get_edge_id_from_edge(e)
                        ).get("random_weight", wt),
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
                        # frm: Original Code:   weight=h.graph.edges[e].get("random_weight", wt),
                        # frm: edges vs. edge_ids:  edge_ids are wanted here (integers)
                        weight=h.graph.edge_data(
                            h.graph.get_edge_id_from_edge(e)
                        ).get("random_weight", wt),
                        subset=frozenset(set(h.graph.nodes) - _part_nodes(node, succ)),
                    )
                )

        return cuts

    # frm: TODO:  Refactor this code to make its two use cases clearer:
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
        
        if (abs(tree_pop - h.ideal_pop) <= h.ideal_pop * h.epsilon) and (
            abs((total_pop - tree_pop) - h.ideal_pop) <= h.ideal_pop * h.epsilon
        ):
            e = (node, pred[node])
            wt = random.random()
            cuts.append(
                Cut(
                    edge=e,
                    # frm: Original Code:  weight=h.graph.edges[e].get("random_weight", wt),
                    # frm: edges vs. edge_ids:  edge_ids are wanted here (integers)
                    weight=h.graph.edge_data(
                        h.graph.get_edge_id_from_edge(e)
                    ).get("random_weight", wt),
                    subset=frozenset(set(h.graph.nodes) - _part_nodes(node, succ)),
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


# frm: ???:  Only ever used once...
# frm: ???: TODO:  Figure out what this does.  There is no NX/RX issue here, I just
#                   don't yet know what it does or why...
def _power_set_sorted_by_size_then_sum(d):
    power_set = [
        s for i in range(1, len(d) + 1) for s in itertools.combinations(d.keys(), i)
    ]

    # Sort the subsets in descending order based on
    # the sum of their corresponding values in the dictionary
    sorted_power_set = sorted(
        power_set, key=lambda s: (len(s), sum(d[i] for i in s)), reverse=True
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
            #frm: This code is a bit dense (at least for me).
            #       Given a cut_edge_list (whose elements have an 
            #       attribute, "edge",) construct a dict
            #       that associates with each "cut" the 
            #       values of the region_surcharge values
            #       for both nodes in the edge.
            #
            #       So, if the region_surcharge dict was
            #       {"muni": 0.2, "water": 0.8} then for 
            #       each cut, cut_n, there would be a
            #       dict value that looked like:
            #       {"muni": ("siteA", "siteA", 
            #        "water": ("water1", "water2")
            #       }
            #
            key: (
                # frm: original code:   populated_graph.graph.nodes[cut.edge[0]].get(key),
                # frm: original code:   populated_graph.graph.nodes[cut.edge[1]].get(key),
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

# frm TODO:  RX version NYI...         def bipartition_tree(
#
#               This might get complicated depending on what kinds of functions
#               are used as parameters.  That is, do the functions used as parameters
#               assume they are working with an NX graph?
#
#               I think all of the functions used as parameters have been converted
#               to work on the new Graph object, but perhaps end users have created
#               their own?  Should probably add logic to verify that the 
#               functions are not written to be operating on an NX Graph.  Not sure
#               how to do that though...
#
# Peter's comments from PR:
#
# Users do sometimes write custom spanning tree and cut edge functions. My 
# recommendation would be to make this simple for now. Have a list of "RX_compatible" 
# functions and then have the MarkovChain class do some coersion to store an 
# appropriate graph and partition object at initialization. We always expect 
# the workflow to be something like
#
#     Graph -> Partition -> MarkovChain
#
# But we do copy operations in each step, so I wouldn't expect any weird 
# side-effects from pushing the determination of what graph type to use 
# off onto the MarkovChain class

# frm: used in this file and in tree_proposals.py
#       But maybe this is intended to be used externally...
#

def bipartition_tree(
    subgraph_to_split: Graph,        # frm: Original code:    graph: nx.Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    spanning_tree: Optional[Graph] = None,     # frm: Original code:    spanning_tree: Optional[nx.Graph] = None,
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
    # frm: TODO:  Change the names of ALL function formal parameters to end in "_fn" - to make it clear
    #               that the paraemter is a function.  This will make it easier to do a global search
    #               to find all function parameters - as well as just being good coding practice...
    """
    This function finds a balanced 2 partition of a graph by drawing a
    spanning tree and finding an edge to cut that leaves at most an epsilon
    imbalance between the populations of the parts. If a root fails, new roots
    are tried until node_repeats in which case a new tree is drawn.

    Builds up a connected subgraph with a connected complement whose population
    is ``epsilon * pop_target`` away from ``pop_target``.

    :param graph: The graph to partition.
    :type graph: nx.Graph
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
    :type spanning_tree: Optional[nx.Graph], optional
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
    if "region_surcharge" in signature(spanning_tree_fn).parameters:
        spanning_tree_fn = partial(spanning_tree_fn, region_surcharge=region_surcharge)

    if "one_sided_cut" in signature(balance_edge_fn).parameters:
        balance_edge_fn = partial(balance_edge_fn, one_sided_cut=one_sided_cut)

    # frm: original code:   populations = {node: graph.nodes[node][pop_col] for node in graph.node_indices}
    populations = {node_id: subgraph_to_split.node_data(node_id)[pop_col] for node_id in subgraph_to_split.node_indices}

    possible_cuts: List[Cut] = []
    if spanning_tree is None:
        # frm TODO:  Make sure spanning_tree_fn operates on new Graph object
        spanning_tree = spanning_tree_fn(subgraph_to_split)

    restarts = 0
    attempts = 0

    while max_attempts is None or attempts < max_attempts:
        if restarts == node_repeats:
            # frm TODO:  Make sure spanning_tree_fn operates on new Graph object
            # frm: ???:  Not sure what this if-stmt is for...
            spanning_tree = spanning_tree_fn(subgraph_to_split)
            restarts = 0
        h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)

        # frm: ???: TODO:  Again - we should NOT be changing semantics based
        #                   on the names in signatures...
        is_region_cut = (
            "region_surcharge" in signature(cut_choice).parameters
            and "populated_graph" in signature(cut_choice).parameters
        )

        # frm:  Find one or more edges in the spanning tree, that if cut would
        #       result in a subtree with the appropriate population.

        # This returns a list of Cut objects with attributes edge and subset
        possible_cuts = balance_edge_fn(h, choice=choice)

        # frm: RX Subgraph 
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
        
    if allow_pair_reselection:
        raise ReselectException(
            f"Failed to find a balanced cut after {max_attempts} attempts.\n"
            f"Selecting a new district pair."
        )

    raise RuntimeError(f"Could not find a possible cut after {max_attempts} attempts.")


# frm TODO:  Note: Re: _bipartition_tree_random_all()  
# 
# There were a couple of interesting issues surrounding this routine in the original code
# related to subgraphs.  The question was whether or not to translate  HERE

# frm: WTF: TODO:  This function has a leading underscore indicating that it is a private
#                   function, but in fact it is used in tree_proposals.py...  It also returns
#                   Cuts which I had hoped would be an internal data structure, but...
# frm: RX-TODO  This is called in tree_proposals.py with a subgraph, so it needs to 
#               return translated Cut objects.  However, it is also called internally in 
#               this code.  I need to make sure that I do not translate the node_ids to the
#               parent_node_ids twice.  At present, they are converted in this file by the 
#               caller, but that won't work in tree_proposals.py, because there it is called
#               with a subgraph, so it would be too late to try to do it in the caller.
#
#               Two options:  1) Have this routine do the translation and then comment the
#               crap out of the call in this file to make sure we do NOT translate them again, or
#               2) figure out a way to get this OUT of tree_proposals.py where it seems it should
#               not be in the first place...
#
def _bipartition_tree_random_all(
    # frm: Note:  Changed the name from "graph" to "subgraph_to_split" to remind any future readers
    #               of the code that the graph passed in is not the partition's graph, and
    #               that any node_ids passed back should be translated into parent_node_ids.
    subgraph_to_split: Graph,                   # frm: Original code:    graph: nx.Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    repeat_until_valid: bool = True,
    spanning_tree: Optional[Graph] = None,     # frm: Original code:    spanning_tree: Optional[nx.Graph] = None,
    spanning_tree_fn: Callable = random_spanning_tree,
    balance_edge_fn: Callable = find_balanced_edge_cuts_memoization,
    choice: Callable = random.choice,
    max_attempts: Optional[int] = 100000,
) -> List[Tuple[Hashable, Hashable]]:    # frm: TODO: Change this to be a set of node_ids (ints)
    """
    Randomly bipartitions a tree into two subgraphs until a valid bipartition is found.

    :param graph: The input graph.
    :type graph: nx.Graph
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
    :type spanning_tree: Optional[nx.Graph], optional
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

    :returns: A list of possible cuts that bipartition the tree into two subgraphs.
    :rtype: List[Tuple[Hashable, Hashable]]

    :raises RuntimeError: If a valid bipartition cannot be found after the specified number of
        attempts.
    """

    # frm: original code:   populations = {node: graph.nodes[node][pop_col] for node in graph.node_indices}
    populations = {
        node_id: subgraph_to_split.node_data(node_id)[pop_col] 
        for node_id in subgraph_to_split.node_indices
    }

    possible_cuts = []
    if spanning_tree is None:
        # frm TODO:  Make sure spanning_tree_fn works on new Graph object
        spanning_tree = spanning_tree_fn(subgraph_to_split)

    restarts = 0
    attempts = 0

    while max_attempts is None or attempts < max_attempts:
        if restarts == node_repeats:
            # frm TODO:  Make sure spanning_tree_fn works on new Graph object
            spanning_tree = spanning_tree_fn(subgraph_to_split)
            restarts = 0
        h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)
        possible_cuts = balance_edge_fn(h, choice=choice)

        # frm: RX-TODO:  Translate cuts into node_id context of the parent.
        if not (repeat_until_valid and len(possible_cuts) == 0):
            # frm: TODO: Remove deubgging code:
            return possible_cuts

        restarts += 1
        attempts += 1

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
    graph: Graph,              # frm: Original code:    graph: nx.Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    repeat_until_valid: bool = True,
    spanning_tree: Optional[Graph] = None,     # frm: Original code:    spanning_tree: Optional[nx.Graph] = None,
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
    :type graph: nx.Graph
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
    :type spanning_tree: Optional[nx.Graph], optional
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
    
    # frm: ???: TODO:  Again - semantics should not depend on signatures...
    if "one_sided_cut" in signature(balance_edge_fn).parameters:
        balance_edge_fn = partial(balance_edge_fn, one_sided_cut=True)

    possible_cuts = _bipartition_tree_random_all(
        subgraph_to_split=graph,
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
    if possible_cuts:
        chosen_cut = choice(possible_cuts)
        num_cuts = len(possible_cuts)
        parent_nodes = graph.translate_subgraph_node_ids_for_set_of_nodes(chosen_cut.subset)
        return num_cuts, frozenset(parent_nodes)  # frm: Not sure if important that it be frozenset
    else:
        # frm: TODO:  Grok when this returns None and why and what the calling code does and why...
        return None

#######################
# frm TODO:  RX version NYI...
def bipartition_tree_random(
    subgraph_to_split: Graph,              # frm: Original code:    graph: nx.Graph,
    pop_col: str,
    pop_target: Union[int, float],
    epsilon: float,
    node_repeats: int = 1,
    repeat_until_valid: bool = True,
    spanning_tree: Optional[Graph] = None,     # frm: Original code:    spanning_tree: Optional[nx.Graph] = None,
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
    :type graph: nx.Graph
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
    :type spanning_tree: Optional[nx.Graph], optional
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
    
    # frm: ???: TODO:  Again - semantics should not depend on signatures...
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

    possible_cuts = _bipartition_tree_random_all(
        subgraph_to_split=subgraph_to_split,
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
    if possible_cuts:
        chosen_cut = choice(possible_cuts)
        translated_nodes = subgraph_to_split.translate_subgraph_node_ids_for_set_of_nodes(chosen_cut.subset)
        return frozenset(translated_nodes)  # frm: Not sure if important that it be frozenset

# frm: used in this file and in tree_proposals.py
#       But maybe this is intended to be used externally...
# frm TODO:  RX version NYI...

# frm: Note that this routine is only used in recom()
def epsilon_tree_bipartition(
    subgraph_to_split: Graph,               # frm: Original code:    graph: nx.Graph,
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
    :type graph: nx.Graph
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
        # frm: original code:   part_pop += graph.nodes[node][pop_col]
        part_pop += subgraph_to_split.node_data(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    remaining_nodes -= nodes

    # All of the remaining nodes go in the last part
    part_pop = 0
    for node in remaining_nodes:
        flips[node] = parts[-1]
        # frm: original code:   part_pop += graph.nodes[node][pop_col]
        part_pop += subgraph_to_split.node_data(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    # translate subgraph node_ids back into node_ids in parent graph
    translated_flips = subgraph_to_split.translate_subgraph_node_ids_for_flips(flips)

    return translated_flips

    # frm: TODO:  I think I need to translate flips elsewhere - need to check...


# TODO: Move these recursive partition functions to their own module. They are not
# central to the operation of the recom function despite being tree methods.
# frm: defined here but only used in partition.py
#       But maybe this is intended to be used externally...
# frm TODO:  RX version NYI...
def recursive_tree_part(
    graph: Graph,                 # frm: Original code:    graph: nx.Graph,
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
    generate initial seed plans or to implement ReCom-like "merge walk" proposals.

    :param graph: The graph to partition into ``len(parts)`` :math:`\varepsilon`-balanced parts.
    :type graph: nx.Graph
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
            nodes = method(
                graph.subgraph(remaining_nodes),
                pop_col=pop_col,
                pop_target=new_pop_target,
                epsilon=(max_pop - min_pop) / (2 * new_pop_target),
                node_repeats=node_repeats,
                one_sided_cut=True,
            )
        except Exception:
            raise

        if nodes is None:
            raise BalanceError()

        part_pop = 0
        for node in nodes:
            flips[node] = part
            # frm: original code:   part_pop += graph.nodes[node][pop_col]
            part_pop += graph.node_data(node)[pop_col]

        if not check_pop(part_pop):
            raise PopulationBalanceError()

        debt += part_pop - pop_target
        remaining_nodes -= nodes

    # After making n-2 districts, we need to make sure that the last
    # two districts are both balanced.

    # frm: For the last call to "method", set one_sided_cut=False to
    #       request that "method" create two equal sized districts
    #       with the given population goal by bisecting the graph.
    nodes = method(
        graph.subgraph(remaining_nodes),
        pop_col=pop_col,
        pop_target=pop_target,
        epsilon=epsilon,
        node_repeats=node_repeats,
        one_sided_cut=False,
    )

    if nodes is None:
        raise BalanceError()

    part_pop = 0
    for node in nodes:
        flips[node] = parts[-2]
        # frm: this code fragment: graph.nodes[node][pop_col] is used
        #       many times and is a candidate for being wrapped with
        #       a function that has a meaningful name, such as perhaps:
        #       get_population_for_node(node, pop_col).  
        #       This is an example of code-bloat from the perspective of
        #       code gurus, but it really helps a new code reviewer understand
        #       WTF is going on...
        # frm: original code:   part_pop += graph.nodes[node][pop_col]
        part_pop += graph.node_data(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    remaining_nodes -= nodes

    # All of the remaining nodes go in the last part
    part_pop = 0
    for node in remaining_nodes:
        flips[node] = parts[-1]
        # frm: original code:   part_pop += graph.nodes[node][pop_col]
        part_pop += graph.node_data(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    return flips

# frm: only used in this file, so I changed the name to have a leading underscore
# frm TODO:  RX version NYI...
def _get_seed_chunks(
    graph: Graph,             # frm: Original code:   graph: nx.Graph,
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
    :type graph: nx.Graph
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
    
    # frm: ??? TODO:  Change the name of num_chunks_left to instead be num_districts_per_chunk.
    # frm: ???: It is not clear to me when num_chunks will not evenly divide num_dists.  In 
    #           the only place where _get_seed_chunks() is called, it is inside an if-stmt
    #           branch that validates that num_chunks evenly divides num_dists...
    #
    num_chunks_left = num_dists // num_chunks

    # frm: ???: TODO:  Change the name of parts below to be something / anything else.  Normally
    #                   parts refers to districts, but here is is just a way to keep track of 
    #                   sets of nodes for chunks.  Yes - they eventually become districts when
    #                   this code gets to the base cases, but I found it confusing at this 
    #                   level...
    #
    parts = range(num_chunks)
    # frm: ???: I think that new_epsilon is the epsilon to use for each district, in which
    #           case the epsilon passed in would be for the  HERE...
    new_epsilon = epsilon / (num_chunks_left * num_chunks)
    if num_chunks_left == 1:
        new_epsilon = epsilon

    chunk_pop = 0
    for node in graph.node_indices:
        # frm: original code:   chunk_pop += graph.nodes[node][pop_col]
        chunk_pop += graph.node_data(node)[pop_col]

    # frm: TODO:  See if there is a better way to structure this instead of a while True loop...
    while True:
        epsilon = abs(epsilon)

        flips = {}
        remaining_nodes = set(graph.nodes)

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
            # frm: original code:   part_pop += graph.nodes[node][pop_col]
            part_pop += graph.node_data(node)[pop_col]
        # frm: ???: Compute what the population total would be for each district in chunk
        part_pop_as_dist = part_pop / num_chunks_left
        fake_epsilon = epsilon
        # frm: ???: If the chunk is for more than one district, divide epsilon by two
        if num_chunks_left != 1:
            fake_epsilon = epsilon / 2
        # frm: ???:  Calculate max and min populations on a district level
        #               This will just be based on epsilon if we only want one district from chunk, but
        #               it will be based on half of epsilon if we want more than one district from chunk.
        #               This is odd - why wouldn't we use an epsilon 
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
    Helper function for recursive_seed_part_inner. Returns the largest prime factor of ``n``
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

# frm: only used in this file
#       But maybe this is intended to be used externally...
# frm TODO:  Peter says this is only ever used internally, so we can add underscore to the name
def recursive_seed_part_inner(
    graph: Graph,           # frm: Original code:    graph: nx.Graph,
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
    Returns a partition with ``num_dists`` districts balanced within ``epsilon`` of
    ``pop_target``.

    frm: ???: TODO:     Correct the above statement that this function returns a partition.
                        In fact, it returns a list of sets of nodes, which is conceptually 
                        equivalent to a partition, but is not a Partition object.  Each
                        set of nodes constitutes a district, but the district does not 
                        have an ID, and there is nothing that associates these nodes
                        with a specific graph - that is implicit, depending on the graph
                        object passed in, so the caller is responsible for knowing that
                        the returned list of sets belongs to the graph passed in...

    Splits graph into num_chunks chunks, and then recursively splits each chunk into
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

    frm: ???:   OK, but why is the logic above for num_chunks the correct number?  Is there
                a mathematical reason for it?  I assume so, but that explanation is missing...

                I presume that the reason is that something in the code that finds a 
                district scales exponentially, so it makes sense to divide and conquer.
                Even so, why this particular strategy for divide and conquer?

    :param graph: The underlying graph structure.
    :type graph: nx.Graph
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
    frm: This code is quite nice once you grok it.

    The goal is to find the given number of districts - but to do it in an
    efficient way - meaning with smaller graphs.  So conceptually, you want 
    to 
    HERE

    There are two base cases when the number of districts still to be found are
    either 1 or 
    
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
            graph.subgraph(graph.node_indices),        # needs to be a subgraph
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            node_repeats=node_repeats,
            one_sided_cut=False,
        )

        # frm: Note to Self:  the name "one_sided_cut" seems unnecessarily opaque.  What it really
        #                       means is whether to split the graph into two equal districts or 
        #                       whether to just find one district from a larger graph.  When we
        #                       clean up this code, consider changing the name of this parameter
        #                       to something like: find_two_equal_sized_districts...
        #
        #                       Consider creating a wrapper function which has the better
        #                       name that delegates to a private method to do the work.

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
        remaining_nodes = set(graph.nodes)
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
        assignment = [nodes] + recursive_seed_part_inner(
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
    # frm: TODO: Add documentation for why a subgraph in call below
    elif num_dists % num_chunks == 0:
        chunks = _get_seed_chunks(
            graph.subgraph(graph.node_indices),     # needs to be a subgraph
            num_chunks,
            num_dists,
            pop_target,
            pop_col,
            epsilon,
            method=partial(method, one_sided_cut=True),
        )

        assignment = []
        for chunk in chunks:
            chunk_assignment = recursive_seed_part_inner(
                graph.subgraph(chunk),
                num_dists // num_chunks,    # new target number of districts
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
        raise Exception("recursive_seed_part_inner(): Should never happen...")

    # The assignment object that has been created needs to have its
    # node_ids translated into parent_node_ids

    translated_assignment = []
    for set_of_nodes in assignment:
        translated_set_of_nodes = graph.translate_subgraph_node_ids_for_set_of_nodes(
            set_of_nodes
        )
        translated_assignment.append(translated_set_of_nodes)

    return translated_assignment



# frm ???:   This routine is never called - not in this file and not in any other GerryChain file.
#               Is it intended to be used by end-users?  And if so, for what purpose?
def recursive_seed_part(
    graph: Graph,         # frm: Original code:    graph: nx.Graph,
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
    Returns a partition with ``num_dists`` districts balanced within ``epsilon`` of
    ``pop_target`` by recursively splitting graph using recursive_seed_part_inner.

    :param graph: The graph
    :type graph: nx.Graph
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
    #               recursive_seed_part_inner(), because the top-level graph has
    #               a _node_id_to_parent_node_id_map that just maps node_ids to themselves.  However,
    #               it seemed a good practice to ALWAYS call routines that are intended
    #               to deal with subgraphs, to use a subgraph even when not strictly 
    #               necessary.  Just one more cognitive load to not have to worry about.
    #
    #               This probably means that the identity _node_id_to_parent_node_id_map for top-level
    #               graphs will never be used, I still think that it makes sense to retain
    #               it - again, for consistency: Every graph knows how to translate to
    #               parent_node_ids even if it is a top-level graph.
    #
    #               In short - an agrument based on invariants being a good thing...
    #
    flips = {}
    assignment = recursive_seed_part_inner(
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


    