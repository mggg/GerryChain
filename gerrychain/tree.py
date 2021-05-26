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
    choice=random.choice
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


def get_seed_chunks(
    graph,
    num_chunks,
    num_dists,
    pop_target,
    pop_col,
    epsilon,
    node_repeats=1,
    method=bipartition_tree_random
):
    """
    Helper function for recursive_seed_part. Partitions the graph into ``num_chunks`` chunks,
    balanced within new_epsilon <= ``epsilon`` of a balanced target population.

    :param graph: The graph
    :param parts: Iterable of part labels (like ``[0,1,2]`` or ``range(4)``
    :param pop_target: target population of the districts (not of the chunks)
    :param pop_col: Node attribute key holding population data
    :param epsilon: How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
        of the partition can be
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.bipartition_tree` to use.
    :return: New assignments for the nodes of ``graph``.
    :rtype: dict
    """
    num_chunks_left = num_dists // num_chunks
    parts = range(num_chunks)
    new_epsilon = epsilon / (num_chunks_left * num_chunks)
    if num_chunks_left == 1:
        new_epsilon = epsilon

    chunk_pop = 0
    for node in graph.nodes:
        chunk_pop += graph.nodes[node][pop_col]

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
            part_pop += graph.nodes[node][pop_col]
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

    chunks = {}
    for key in flips.keys():
        if flips[key] not in chunks.keys():
            chunks[flips[key]] = []
        chunks[flips[key]].append(key)

    return list(chunks.values())


def get_max_prime_factor_less_than(
    n, ceil
):
    """
    Helper function for recursive_seed_part. Returns the largest prime factor of ``n`` less than
    ``ceil``, or None if all are greater than ceil.
    """
    factors = []
    i = 2
    while i * i <= n:
        if n % i:
            i += 1
        else:
            n //= i
            factors.append(i)
    if n > 1:
        factors.append(n)

    if len(factors) == 0:
        return 1
    m = [i for i in factors if i <= ceil]
    if m == []:
        return None
    return int(max(m))


def recursive_seed_part_inner(
    graph,
    num_dists,
    pop_target,
    pop_col,
    epsilon,
    method=bipartition_tree,
    node_repeats=1,
    n=None,
    ceil=None,
):
    """
    Inner function for recursive_seed_part.
    Returns a partition with ``num_dists`` districts balanced within ``epsilon`` of
    ``pop_target``.
    Splits graph into num_chunks chunks, and then recursively splits each chunk into
    ``num_dists``/num_chunks chunks.
    The number num_chunks of chunks is chosen based on ``n`` and ``ceil`` as follows:
        If ``n`` is None, and ``ceil`` is None, num_chunks is the largest prime factor
        of ``num_dists``.
        If ``n`` is None and ``ceil`` is an integer at least 2, then num_chunks is the
        largest prime factor of ``num_dists`` that is less than ``ceil``
        If ``n`` is a positive integer, num_chunks equals n.
    Finally, if the number of chunks as chosen above does not divide ``num_dists``, then
    this function bites off a single district from the graph and recursively partitions
    the remaining graph into ``num_dists``-1 districts.

    :param graph: The graph
    :param num_dists: number of districts to partition the graph into
    :param pop_target: Target population for each part of the partition
    :param pop_col: Node attribute key holding population data
    :param epsilon: How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
        of the partition can be
    :param method: Function used to find balanced partitions at the 2-district level
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.bipartition_tree` to use.
    :param n: Either a positive integer (greater than 1) or None. If n is a positive integer,
        this function will recursively create a seed plan by either biting off districts from
        graph or dividing graph into n chunks and recursing into each of these. If n is None,
        this function prime factors ``num_dists``=n_1*n_2*...*n_k (n_1 > n_2 > ... n_k) and
        recursively partitions graph into n_1 chunks.
    :param ceil: Either a positive integer (at least 2) or None. Relevant only if n is None.
        If ``ceil`` is a positive integer then finds the largest factor of ``num_dists`` less
        than or equal to ``ceil``, and recursively splits graph into that number of chunks, or
        bites off a district if that number is 1.
    :return: New assignments for the nodes of ``graph``.
    :rtype: List of lists, each list is a district
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

    # bite off a district and recurse into the remaining subgraph
    elif num_chunks is None or num_dists % num_chunks != 0:
        remaining_nodes = set(graph.nodes)
        nodes = method(
            graph.subgraph(remaining_nodes),
            pop_col=pop_col,
            pop_target=pop_target,
            epsilon=epsilon,
            node_repeats=node_repeats
        )
        remaining_nodes -= nodes
        assignment = [nodes] + recursive_seed_part_inner(graph.subgraph(remaining_nodes),
            num_dists - 1,
            pop_target,
            pop_col,
            epsilon,
            n=n,
            ceil=ceil)

    # split graph into num_chunks chunks, and recurse into each chunk
    elif num_dists % num_chunks == 0:
        chunks = get_seed_chunks(
            graph,
            num_chunks,
            num_dists,
            pop_target,
            pop_col,
            epsilon,
            method=method
        )

        assignment = []
        for chunk in chunks:
            chunk_assignment = recursive_seed_part_inner(
                graph.subgraph(chunk),
                num_dists // num_chunks,
                pop_target,
                pop_col,
                epsilon,
                n=n,
                ceil=ceil
            )
            assignment += chunk_assignment

    return assignment


def recursive_seed_part(
    graph,
    parts,
    pop_target,
    pop_col,
    epsilon,
    method=bipartition_tree,
    node_repeats=1,
    n=None,
    ceil=None
):
    """
    Returns a partition with ``num_dists`` districts balanced within ``epsilon`` of
    ``pop_target`` by recursively splitting graph using recursive_seed_part_inner.

    :param graph: The graph
    :param parts: Iterable of part labels (like ``[0,1,2]`` or ``range(4)``
    :param pop_target: Target population for each part of the partition
    :param pop_col: Node attribute key holding population data
    :param epsilon: How far (as a percentage of ``pop_target``) from ``pop_target`` the parts
        of the partition can be
    :param method: Function used to find balanced partitions at the 2-district level
    :param node_repeats: Parameter for :func:`~gerrychain.tree_methods.bipartition_tree` to use.
    :param n: Either a positive integer (greater than 1) or None. If n is a positive integer,
    this function will recursively create a seed plan by either biting off districts from graph
    or dividing graph into n chunks and recursing into each of these. If n is None, this
    function prime factors ``num_dists``=n_1*n_2*...*n_k (n_1 > n_2 > ... n_k) and recursively
    partitions graph into n_1 chunks.
    :param ceil: Either a positive integer (at least 2) or None. Relevant only if n is None. If
    ``ceil`` is a positive integer then finds the largest factor of ``num_dists`` less than or
    equal to ``ceil``, and recursively splits graph into that number of chunks, or bites off a
    district if that number is 1.
    :return: New assignments for the nodes of ``graph``.
    :rtype: dict
    """
    flips = {}
    assignment = recursive_seed_part_inner(
        graph,
        len(parts),
        pop_target,
        pop_col,
        epsilon,
        method=bipartition_tree,
        node_repeats=node_repeats,
        n=n,
        ceil=ceil
    )
    for i in range(len(assignment)):
        for node in assignment[i]:
            flips[node] = parts[i]
    return flips


class BalanceError(Exception):
    """Raised when a balanced cut cannot be found."""
