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

from .._deprecated import (
    deprecated_lazy_alias,
    legacy_bipartition_tree_random,
    legacy_epsilon_tree_bipartition,
    legacy_predecessors,
    legacy_successors,
)
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

predecessors = legacy_predecessors
successors = legacy_successors
bipartition_tree_random = legacy_bipartition_tree_random
epsilon_tree_bipartition = legacy_epsilon_tree_bipartition
recursive_tree_part = deprecated_lazy_alias(
    "gerrychain.tree.recursive_tree_part",
    "gerrychain.partition.recursive_tree_part",
    "gerrychain.partition.initial_partition_generators",
    "recursive_tree_part",
)
recursive_seed_part = deprecated_lazy_alias(
    "gerrychain.tree.recursive_seed_part",
    "gerrychain.partition.recursive_seed_part",
    "gerrychain.partition.initial_partition_generators",
    "recursive_seed_part",
)
get_max_prime_factor_less_than = deprecated_lazy_alias(
    "gerrychain.tree.get_max_prime_factor_less_than",
    "gerrychain.partition.initial_partition_generators.get_max_prime_factor_less_than",
    "gerrychain.partition.initial_partition_generators",
    "get_max_prime_factor_less_than",
)

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
    "predecessors",
    "successors",
    "bipartition_tree_random",
    "epsilon_tree_bipartition",
    "recursive_tree_part",
    "recursive_seed_part",
    "get_max_prime_factor_less_than",
]
