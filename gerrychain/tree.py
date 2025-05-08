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
- A suite of functions (`bipartition_tree`, `recursive_tree_part`, `get_seed_chunks`, etc.)
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

import networkx as nx
# frm TODO:     Remove import of networkx once we have moved networkx
#               dependencies out of this file - see comments below on 
#               spanning trees.

from networkx.algorithms import tree
# frm TODO:     Remove import of "tree" from networkx.algorithms in this file
#               It is only used to get a spanning tree function:
#
#                   spanning_tree = tree.minimum_spanning_tree(
#
#               There is an RX function that also computes a spanning tree - hopefully
#               it works as we want it to work and hence can be used.
#
#               I think it probably makes sense to move this spanning tree function
#               into graph.py and to encapsulate the NX vs RX code there.

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

# frm TODO:  RX version NYI...
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
    if region_surcharge is None:
        region_surcharge = dict()

    #frm ???: Does graph.edges() return two edges for every actual edge?
    #           For example, if there is an edge from node 1 to node 2
    #           then I think there are actually two edges in the graph,
    #           (1,2) and (2,1) so the question is whether graph.edges()
    #           returns both of these or if it just returns one of them,
    #           and if only one - then which one?
    for edge in graph.edges():
        weight = random.random()
        for key, value in region_surcharge.items():
            # We surcharge edges that cross regions and those that are not in any region
            if (
                # frm: original code:   graph.nodes[edge[0]][key] != graph.nodes[edge[1]][key]
                # frm: original code:   or graph.nodes[edge[0]][key] is None
                # frm: original code:   or graph.nodes[edge[1]][key] is None
                graph.get_node_data_dict(edge[0])[key] != graph.get_node_data_dict(edge[1])[key]
                or graph.get_node_data_dict(edge[0])[key] is None
                or graph.get_node_data_dict(edge[1])[key] is None
            ):
                weight += value

        graph.edges[edge]["random_weight"] = weight

    # frm TODO:  RX version NYI...      def random_spanning_tree(
    #
    #   There is an RX version of a minimum spanning tree:
    #
    #       https://www.rustworkx.org/apiref/rustworkx.minimum_spanning_tree.html
    #
    #   The NX version is documemted here:
    #
    #       https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.tree.mst.minimum_spanning_tree.html
    #
    #   Need to see if the RX version actually does the same thing...
    #
    
    # frm TODO: Remove this hack once I have a minimum spanning tree function that works
    #           on both NX and RX Graphs and is nicely encapsulated...
    #
    #           The hack is that at present, I only have a spanning tree function that works
    #           on NX Graphs, so I evilly reach into the new Graph object to get the NX Graph
    #           and I then use an NX function to compute the spanning tree, and I then convert
    #           that spanning tree back into a new Graph object.
    #
    #           This will NOT work once we automatically convert the internal graph inside the
    #           new Graph object from NX to RX when we create a Partition.
    #
    #           Ticking time bomb...
    #
    nxgraph = graph.getNxGraph()

    # frm TODO:  Implement a new minimum_spanning_tree routine that works for both NX and RX
    spanning_tree = tree.minimum_spanning_tree(
        nxgraph, algorithm="kruskal", weight="random_weight"
    )
    # frm: CROCK/HACK/KLUGE: TODO:  This routine needs to return a new Graph object.  This code
    #                               converts the spanning tree from tree.minimum_spanning_tree() to a new Graph...
    spanning_nxgraph = nx.Graph(spanning_tree)
    spanningGraph = Graph.from_networkx(spanning_nxgraph)

    return spanningGraph


# frm TODO:  RX version NYI...
def uniform_spanning_tree(
    graph: Graph,          # frm: Original code:    graph: nx.Graph, choice: Callable = random.choice
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
    root = choice(list(graph.node_indices))
    tree_nodes = set([root])
    next_node = {root: None}

    for node in graph.node_indices:
        u = node
        while u not in tree_nodes:
            next_node[u] = choice(list(graph.neighbors(u)))
            u = next_node[u]

        u = node
        while u not in tree_nodes:
            tree_nodes.add(u)
            u = next_node[u]

    # frm TODO:  RX version NYI...
    #               This looks OK - just need add_edge() to work for both NX and RX

    G = Graph()                 # frm: Original code:    G = nx.Graph()
    for node in tree_nodes:
        if next_node[node] is not None:
            # frm: RustworkX requires a third param for the edge payload...
            #       However, there is an rx.add_edges_from_no_data()
            G.add_edge(node, next_node[node])

    return G


# frm TODO  RX version NYI...
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


# Tuple that is used in the find_balanced_edge_cuts function
Cut = namedtuple("Cut", "edge weight subset")
Cut.__new__.__defaults__ = (None, None, None)
Cut.__doc__ = "Represents a cut in a graph."
Cut.edge.__doc__ = "The edge where the cut is made. Defaults to None."
Cut.weight.__doc__ = "The weight assigned to the edge (if any). Defaults to None."
Cut.subset.__doc__ = (
    "The (frozen) subset of nodes on one side of the cut. Defaults to None."
)


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
    leaves = deque(x for x in h if h.degree(x) == 1)
    while len(leaves) > 0:
        leaf = leaves.popleft()
        if h.has_ideal_population(leaf, one_sided_cut=one_sided_cut):
            e = (leaf, pred[leaf])
            cuts.append(
                Cut(
                    edge=e,
                    weight=h.graph.edges[e].get("random_weight", random.random()),
                    subset=frozenset(h.subsets[leaf].copy()),
                )
            )
        # Contract the leaf:
        parent = pred[leaf]
        h.contract_node(leaf, parent)
        if h.degree(parent) == 1 and parent != root:
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

    root = choice([x for x in h if h.degree(x) > 1])
    # frm: Original code:   pred = predecessors(h.graph, root)
    # frm: Original code:   succ = successors(h.graph, root)
    pred = h.graph.predecessors(root)
    succ = h.graph.successors(root)
    total_pop = h.tot_pop

    subtree_pops = _calc_pops(succ, root, h)

    cuts = []

    if one_sided_cut:
        for node, tree_pop in subtree_pops.items():
            if abs(tree_pop - h.ideal_pop) <= h.ideal_pop * h.epsilon:
                e = (node, pred[node])
                wt = random.random()
                cuts.append(
                    Cut(
                        edge=e,
                        weight=h.graph.edges[e].get("random_weight", wt),
                        subset=frozenset(_part_nodes(node, succ)),
                    )
                )
            elif abs((total_pop - tree_pop) - h.ideal_pop) <= h.ideal_pop * h.epsilon:
                e = (node, pred[node])
                wt = random.random()
                cuts.append(
                    Cut(
                        edge=e,
                        weight=h.graph.edges[e].get("random_weight", wt),
                        subset=frozenset(set(h.graph.nodes) - _part_nodes(node, succ)),
                    )
                )

        return cuts

    for node, tree_pop in subtree_pops.items():
        if (abs(tree_pop - h.ideal_pop) <= h.ideal_pop * h.epsilon) and (
            abs((total_pop - tree_pop) - h.ideal_pop) <= h.ideal_pop * h.epsilon
        ):
            e = (node, pred[node])
            wt = random.random()
            cuts.append(
                Cut(
                    edge=e,
                    weight=h.graph.edges[e].get("random_weight", wt),
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

    return max(cut_edge_list, key=lambda cut: cut.weight)


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
                populated_graph.graph.get_node_data_dict(cut.edge[0]).get(key),
                populated_graph.graph.get_node_data_dict(cut.edge[1]).get(key),
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

# frm: used in this file and in tree_proposals.py
#       But maybe this is intended to be used externally...

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
def bipartition_tree(
    graph: Graph,        # frm: Original code:    graph: nx.Graph,
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
    populations = {node: graph.get_node_data_dict(node)[pop_col] for node in graph.node_indices}

    possible_cuts: List[Cut] = []
    if spanning_tree is None:
        # frm TODO:  Make sure spanning_tree_fn operates on new Graph object
        spanning_tree = spanning_tree_fn(graph)

    restarts = 0
    attempts = 0

    while max_attempts is None or attempts < max_attempts:
        if restarts == node_repeats:
            # frm TODO:  Make sure spanning_tree_fn operates on new Graph object
            spanning_tree = spanning_tree_fn(graph)
            restarts = 0
        h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)

        is_region_cut = (
            "region_surcharge" in signature(cut_choice).parameters
            and "populated_graph" in signature(cut_choice).parameters
        )

        # This returns a list of Cut objects with attributes edge and subset
        possible_cuts = balance_edge_fn(h, choice=choice)

        if len(possible_cuts) != 0:
            if is_region_cut:
                return cut_choice(h, region_surcharge, possible_cuts).subset

            return cut_choice(possible_cuts).subset

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


# frm TODO:  RX version NYI...
def _bipartition_tree_random_all(
    graph: Graph,                   # frm: Original code:    graph: nx.Graph,
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
) -> List[Tuple[Hashable, Hashable]]:
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
    populations = {node: graph.get_node_data_dict(node)[pop_col] for node in graph.node_indices}

    possible_cuts = []
    if spanning_tree is None:
        # frm TODO:  Make sure spanning_tree_fn works on new Graph object
        spanning_tree = spanning_tree_fn(graph)

    restarts = 0
    attempts = 0

    while max_attempts is None or attempts < max_attempts:
        if restarts == node_repeats:
            # frm TODO:  Make sure spanning_tree_fn works on new Graph object
            spanning_tree = spanning_tree_fn(graph)
            restarts = 0
        h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)
        possible_cuts = balance_edge_fn(h, choice=choice)

        if not (repeat_until_valid and len(possible_cuts) == 0):
            return possible_cuts

        restarts += 1
        attempts += 1

    raise RuntimeError(f"Could not find a possible cut after {max_attempts} attempts.")

# frm: used in this file and in tree_proposals.py
#       But maybe this is intended to be used externally...

# frm TODO:  RX version NYI...
def bipartition_tree_random(
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
    if "one_sided_cut" in signature(balance_edge_fn).parameters:
        balance_edge_fn = partial(balance_edge_fn, one_sided_cut=True)

    possible_cuts = _bipartition_tree_random_all(
        graph=graph,
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
        return choice(possible_cuts).subset

# frm: used in this file and in tree_proposals.py
#       But maybe this is intended to be used externally...
# frm TODO:  RX version NYI...

def epsilon_tree_bipartition(
    graph: Graph,               # frm: Original code:    graph: nx.Graph,
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
    remaining_nodes = graph.node_indices

    lb_pop = pop_target * (1 - epsilon)
    ub_pop = pop_target * (1 + epsilon)
    check_pop = lambda x: lb_pop <= x <= ub_pop

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
        # frm: original code:   part_pop += graph.nodes[node][pop_col]
        part_pop += graph.get_node_data_dict(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    remaining_nodes -= nodes

    # All of the remaining nodes go in the last part
    part_pop = 0
    for node in remaining_nodes:
        flips[node] = parts[-1]
        # frm: original code:   part_pop += graph.nodes[node][pop_col]
        part_pop += graph.get_node_data_dict(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    return flips


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
            part_pop += graph.get_node_data_dict(node)[pop_col]

        if not check_pop(part_pop):
            raise PopulationBalanceError()

        debt += part_pop - pop_target
        remaining_nodes -= nodes

    # After making n-2 districts, we need to make sure that the last
    # two districts are both balanced.
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
        part_pop += graph.get_node_data_dict(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    remaining_nodes -= nodes

    # All of the remaining nodes go in the last part
    part_pop = 0
    for node in remaining_nodes:
        flips[node] = parts[-1]
        # frm: original code:   part_pop += graph.nodes[node][pop_col]
        part_pop += graph.get_node_data_dict(node)[pop_col]

    if not check_pop(part_pop):
        raise PopulationBalanceError()

    return flips

# frm: only used in this file 
#       But maybe this is intended to be used externally...
# frm TODO:  RX version NYI...
def get_seed_chunks(
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
    num_chunks_left = num_dists // num_chunks
    parts = range(num_chunks)
    new_epsilon = epsilon / (num_chunks_left * num_chunks)
    if num_chunks_left == 1:
        new_epsilon = epsilon

    chunk_pop = 0
    for node in graph.node_indices:
        # frm: original code:   chunk_pop += graph.nodes[node][pop_col]
        chunk_pop += graph.get_node_data_dict(node)[pop_col]

    while True:
        epsilon = abs(epsilon)

        flips = {}
        remaining_nodes = set(graph.nodes)

        min_pop = pop_target * (1 - new_epsilon) * num_chunks_left
        max_pop = pop_target * (1 + new_epsilon) * num_chunks_left

        chunk_pop_target = chunk_pop / num_chunks

        diff = min(max_pop - chunk_pop_target, chunk_pop_target - min_pop)
        new_new_epsilon = diff / chunk_pop_target

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

        part_pop = 0
        for node in remaining_nodes:
            # frm: original code:   part_pop += graph.nodes[node][pop_col]
            part_pop += graph.get_node_data_dict(node)[pop_col]
        part_pop_as_dist = part_pop / num_chunks_left
        fake_epsilon = epsilon
        if num_chunks_left != 1:
            fake_epsilon = epsilon / 2
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
# frm TODO:  RX version NYI...
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

    # Chooses num_chunks
    if n is None:
        if ceil is None:
            num_chunks = get_max_prime_factor_less_than(num_dists, num_dists)
        elif ceil >= 2:
            num_chunks = get_max_prime_factor_less_than(num_dists, ceil)
        else:
            raise ValueError("ceil must be None or at least 2")
    elif n > 1:
        num_chunks = n
    else:
        raise ValueError("n must be None or a positive integer")

    # base case
    if num_dists == 1:
        return [set(graph.nodes)]

    # frm TODO:   Check that all the possible "method" functions take the new Graph arg as first param
    if num_dists == 2:
        nodes = method(
            graph,
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            node_repeats=node_repeats,
            one_sided_cut=False,
        )

        return [set(nodes), set(graph.nodes) - set(nodes)]

    # bite off a district and recurse into the remaining subgraph
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
    elif num_dists % num_chunks == 0:
        chunks = get_seed_chunks(
            graph,
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
                num_dists // num_chunks,
                pop_target,
                pop_col,
                epsilon,
                method,
                n=n,
                ceil=ceil,
            )
            assignment += chunk_assignment

    return assignment

# frm ???:   This routine is never called - not in this file and not in any other GerryChain file.
#               Is it intended to be used by end-users?  And if so, for what purpose?
# frm TODO:  RX version NYI...
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
    flips = {}
    assignment = recursive_seed_part_inner(
        graph,
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
