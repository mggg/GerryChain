"""
GerryChain creates district plans where a district is a set of nodes
in a graph that satisfy the specified conditions - for example, having
an appropriate population.

This module implements the algorithms that decide what nodes belong
in a district (often called a "part" in the code).

There are two sub-modules that provide these implementations:

spanning_tree.py implements functions to create a spanning tree for
a graph (or subgraph).  Spanning trees are fundamental to how
GerryChain works - they convert a graph into a tree that can
then be traversed bottom up to compute population totals for
each subtree, which then allows the code to identify subtrees that
can form a district (part).

bipartition.py implements the code that walks spanning trees to
identify sets of nodes that are candidates for becoming a
district (part).

There is additional documentation in each of these sub-modules.

"""

from .bipartition_tree import (
    BalanceError,
    BipartitionTreeFn,
    BipartitionWarning,
    PopulationBalanceError,
    ReComBipartitionTreeFn,
    ReselectException,
    bipartition_tree,
    bipartition_tree_random_with_num_cuts,
    find_balanced_edge_cuts_contraction,
    find_balanced_edge_cuts_memoization,
)
from .spanning_tree import random_spanning_tree, uniform_spanning_tree

__all__ = [
    "bipartition_tree",
    "bipartition_tree_random_with_num_cuts",
    "find_balanced_edge_cuts_contraction",
    "find_balanced_edge_cuts_memoization",
    "BalanceError",
    "PopulationBalanceError",
    "ReselectException",
    "BipartitionWarning",
    "BipartitionTreeFn",
    "ReComBipartitionTreeFn",
    "uniform_spanning_tree",
    "random_spanning_tree",
]
