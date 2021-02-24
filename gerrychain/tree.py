import networkx as nx
from networkx.algorithms import tree

from .random import random
from collections import deque, namedtuple


def predecessors(h, root):
    return {a: b for a, b in nx.bfs_predecessors(h, root)}


def successors(h, root):
    return {a: b for a, b in nx.bfs_successors(h, root)}


def random_spanning_tree(graph):
    """ Builds a spanning tree chosen by Kruskal's method using random weights.
        :param graph: Networkx Graph

        Important Note:
        The key is specifically labelled "random_weight" instead of the previously
        used "weight". Turns out that networkx uses the "weight" keyword for other
        operations, like when computing the laplacian or the adjacency matrix.
        This meant that the laplacian would change for the graph step to step,
        something that we do not intend!!
    """
    for edge in graph.edges:
        graph.edges[edge]["random_weight"] = random.random()

    spanning_tree = tree.maximum_spanning_tree(
        graph, algorithm="kruskal", weight="random_weight"
    )
    return spanning_tree


def uniform_spanning_tree(graph, choice=random.choice):
    """ Builds a spanning tree chosen uniformly from the space of all
        spanning trees of the graph.
        :param graph: Networkx Graph
        :param choice: :func:`random.choice`
    """
    root = choice(list(graph.nodes))
    tree_nodes = set([root])
    next_node = {root: None}

    for node in graph.nodes:
        u = node
        while u not in tree_nodes:
            next_node[u] = choice(list(nx.neighbors(graph, u)))
            u = next_node[u]

        u = node
        while u not in tree_nodes:
            tree_nodes.add(u)
            u = next_node[u]

    G = nx.Graph()
    for node in tree_nodes:
        if next_node[node] is not None:
            G.add_edge(node, next_node[node])

    return G


class PopulatedGraph:
    def __init__(self, graph, populations, ideal_pop, epsilon):
        self.graph = graph
        self.subsets = {node: {node} for node in graph}
        self.population = populations.copy()
        self.tot_pop = sum(self.population.values())
        self.ideal_pop = ideal_pop
        self.epsilon = epsilon
        self._degrees = {node: graph.degree(node) for node in graph}

    def __iter__(self):
        return iter(self.graph)

    def degree(self, node):
        return self._degrees[node]

    def contract_node(self, node, parent):
        self.population[parent] += self.population[node]
        self.subsets[parent] |= self.subsets[node]
        self._degrees[parent] -= 1

    def has_ideal_population(self, node):
        return (
            abs(self.population[node] - self.ideal_pop) < self.epsilon * self.ideal_pop
        )


Cut = namedtuple("Cut", "edge subset")


def find_balanced_edge_cuts_contraction(h, choice=random.choice):
    # this used to be greater than 2 but failed on small grids:(
    root = choice([x for x in h if h.degree(x) > 1])
    # BFS predecessors for iteratively contracting leaves
    pred = predecessors(h.graph, root)

    cuts = []
    leaves = deque(x for x in h if h.degree(x) == 1)
    while len(leaves) > 0:
        leaf = leaves.popleft()
        if h.has_ideal_population(leaf):
            cuts.append(Cut(edge=(leaf, pred[leaf]), subset=h.subsets[leaf].copy()))
        # Contract the leaf:
        parent = pred[leaf]
        h.contract_node(leaf, parent)
        if h.degree(parent) == 1 and parent != root:
            leaves.append(parent)
    return cuts


def find_balanced_edge_cuts_memoization(h, choice=random.choice):
    root = choice([x for x in h if h.degree(x) > 1])
    pred = predecessors(h.graph, root)
    succ = successors(h.graph, root)
    total_pop = h.tot_pop
    subtree_pops = {}
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

    cuts = []
    for node, tree_pop in subtree_pops.items():

        def part_nodes(start):
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

        if abs(tree_pop - h.ideal_pop) <= h.ideal_pop * h.epsilon:
            cuts.append(Cut(edge=(node, pred[node]), subset=part_nodes(node)))
        elif abs((total_pop - tree_pop) - h.ideal_pop) <= h.ideal_pop * h.epsilon:
            cuts.append(Cut(edge=(node, pred[node]),
                            subset=set(h.graph.nodes) - part_nodes(node)))
    return cuts


def bipartition_tree(
    graph,
    pop_col,
    pop_target,
    epsilon,
    node_repeats=1,
    spanning_tree=None,
    spanning_tree_fn=random_spanning_tree,
    balance_edge_fn=find_balanced_edge_cuts_memoization,
    choice=random.choice,
):
    """This function finds a balanced 2 partition of a graph by drawing a
    spanning tree and finding an edge to cut that leaves at most an epsilon
    imbalance between the populations of the parts. If a root fails, new roots
    are tried until node_repeats in which case a new tree is drawn.

    Builds up a connected subgraph with a connected complement whose population
    is ``epsilon * pop_target`` away from ``pop_target``.

    Returns a subset of nodes of ``graph`` (whose induced subgraph is connected).
    The other part of the partition is the complement of this subset.

    :param graph: The graph to partition
    :param pop_col: The node attribute holding the population of each node
    :param pop_target: The target population for the returned subset of nodes
    :param epsilon: The allowable deviation from  ``pop_target`` (as a percentage of
        ``pop_target``) for the subgraph's population
    :param node_repeats: A parameter for the algorithm: how many different choices
        of root to use before drawing a new spanning tree.
    :param spanning_tree: The spanning tree for the algorithm to use (used when the
        algorithm chooses a new root and for testing)
    :param spanning_tree_fn: The random spanning tree algorithm to use if a spanning
        tree is not provided
    :param choice: :func:`random.choice`. Can be substituted for testing.
    """
    populations = {node: graph.nodes[node][pop_col] for node in graph}

    possible_cuts = []
    if spanning_tree is None:
        spanning_tree = spanning_tree_fn(graph)
    restarts = 0
    while len(possible_cuts) == 0:
        if restarts == node_repeats:
            spanning_tree = spanning_tree_fn(graph)
            restarts = 0
        h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)
        possible_cuts = balance_edge_fn(h, choice=choice)
        restarts += 1

    return choice(possible_cuts).subset


def bipartition_tree_random(
    graph,
    pop_col,
    pop_target,
    epsilon,
    node_repeats=1,
    repeat_until_valid=True,
    spanning_tree=None,
    spanning_tree_fn=random_spanning_tree,
    balance_edge_fn=find_balanced_edge_cuts_memoization,
    choice=random.choice,
):
    """This is like :func:`bipartition_tree` except it chooses a random balanced
    cut, rather than the first cut it finds.

    This function finds a balanced 2 partition of a graph by drawing a
    spanning tree and finding an edge to cut that leaves at most an epsilon
    imbalance between the populations of the parts. If a root fails, new roots
    are tried until node_repeats in which case a new tree is drawn.

    Builds up a connected subgraph with a connected complement whose population
    is ``epsilon * pop_target`` away from ``pop_target``.

    Returns a subset of nodes of ``graph`` (whose induced subgraph is connected).
    The other part of the partition is the complement of this subset.

    :param graph: The graph to partition
    :param pop_col: The node attribute holding the population of each node
    :param pop_target: The target population for the returned subset of nodes
    :param epsilon: The allowable deviation from  ``pop_target`` (as a percentage of
        ``pop_target``) for the subgraph's population
    :param node_repeats: A parameter for the algorithm: how many different choices
        of root to use before drawing a new spanning tree.
    :param repeat_until_valid: Determines whether to keep drawing spanning trees
        until a tree with a balanced cut is found. If `True`, a set of nodes will
        always be returned; if `False`, `None` will be returned if a valid spanning
        tree is not found on the first try.
    :param spanning_tree: The spanning tree for the algorithm to use (used when the
        algorithm chooses a new root and for testing)
    :param spanning_tree_fn: The random spanning tree algorithm to use if a spanning
        tree is not provided
    :param balance_edge_fn: The algorithm used to find balanced cut edges
    :param choice: :func:`random.choice`. Can be substituted for testing.
    """
    populations = {node: graph.nodes[node][pop_col] for node in graph}

    possible_cuts = []
    if spanning_tree is None:
        spanning_tree = spanning_tree_fn(graph)

    repeat = True
    while repeat and len(possible_cuts) == 0:
        spanning_tree = spanning_tree_fn(graph)
        h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)
        possible_cuts = balance_edge_fn(h, choice=choice)
        repeat = repeat_until_valid

    if possible_cuts:
        return choice(possible_cuts).subset
    return None


def recursive_tree_part(
    graph, parts, pop_target, pop_col, epsilon, node_repeats=1, method=bipartition_tree
):
    """Uses :func:`~gerrychain.tree.bipartition_tree` recursively to partition a tree into
    ``len(parts)`` parts of population ``pop_target`` (within ``epsilon``). Can be used to
    generate initial seed plans or to implement ReCom-like "merge walk" proposals.

    :param graph: The graph
    :param parts: Iterable of part labels (like ``[0,1,2]`` or ``range(4)``
    :param pop_target: Target population for each part of the partition
    :param pop_col: Node attribute key holding population data
    :param epsilon: How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
        of the partition can be
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.bipartition_tree` to use.
    :return: New assignments for the nodes of ``graph``.
    :rtype: dict
    """
    flips = {}
    remaining_nodes = set(graph.nodes)
    # We keep a running tally of deviation from ``epsilon`` at each partition
    # and use it to tighten the population constraints on a per-partition
    # basis such that every partition, including the last partition, has a
    # population within +/-``epsilon`` of the target population.
    # For instance, if district n's population exceeds the target by 2%
    # with a +/-2% epsilon, then district n+1's population should be between
    # 98% of the target population and the target population.
    debt = 0

    for part in parts[:-1]:
        min_pop = max(pop_target * (1 - epsilon), pop_target * (1 - epsilon) - debt)
        max_pop = min(pop_target * (1 + epsilon), pop_target * (1 + epsilon) - debt)
        nodes = method(
            graph.subgraph(remaining_nodes),
            pop_col=pop_col,
            pop_target=(min_pop + max_pop) / 2,
            epsilon=(max_pop - min_pop) / (2 * pop_target),
            node_repeats=node_repeats,
        )

        if nodes is None:
            raise BalanceError()

        part_pop = 0
        for node in nodes:
            flips[node] = part
            part_pop += graph.nodes[node][pop_col]
        debt += part_pop - pop_target
        remaining_nodes -= nodes

    # All of the remaining nodes go in the last part
    for node in remaining_nodes:
        flips[node] = parts[-1]

    return flips


class BalanceError(Exception):
    """Raised when a balanced cut cannot be found."""
