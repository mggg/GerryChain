"""
Collection of constraint functions for the validation step in RunDMCMC.

=========================== ==============================================
Helper classes
==========================================================================
Validator                   Collection of constraints
Bounds                      Bounds on numeric constraints
UpperBounds                 Upper bounds on numeric constraints
LowerBounds                 Lower bounds on numeric constraints
SelfConfiguringUpperBound   Automatic upper bounds on numeric constraints
SelfConfiguringLowerBound   Automatic lower bounds on numeric constraints
WithinPercentRangeOfBounds  Percentage bounds for numeric constraints
==========================================================================

|

============================================== ==============================================
Boolean constraint functions
=============================================================================================
no_worse_L1_reciprocal_polsby_popper            Lower bounded L1-reciprocal Polsby-Popper
no_worse_L_minus_1_reciprocal_polsby_popper     Lower bounded L(-1)-reciprocal Polsby-Popper
single_flip_contiguous                          Contiguity of districts after single flips
contiguous                                      Contiguity of districts with NetworkX methods
no_more_disconnected                            No more disconnected districts than initially
no_vanishing_districts                          No districts may be completely consumed
=============================================================================================

Each new step proposed to the chain is passed off to the "validator" functions
here to determine whether or not the step is valid. If it is invalid (breaks
contiguity, for instance), then the step is immediately rejected.

The signature of a validator function should be as follows::

    def validator(partition):
        # check if valid
        # ...
        return is_valid

That is, validators take in a :class:`~rundmcmc.partition.Partition` instance,
and should return whether or not the instance is valid according to their
rules. Many top-level functions following this signature in this module are
examples of this.

"""

import collections
import random

import networkx as nx
import networkx.algorithms.shortest_paths.weighted as nx_path
from networkx import NetworkXNoPath

from rundmcmc.updaters import CountySplit


class Validator:
    """
    Collection of validity checks passed to
    :class:`rundmcmc.chain.MarkovChain`.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if all validators pass, and ``False`` if any one fails.

    """
    def __init__(self, constraints):
        """:constraints: List of validator functions that will check partitions."""
        self.constraints = constraints

    def __call__(self, partition):
        """Determine if the given partition is valid.

        :partition: :class:`Partition` class to check.

        """
        # check each constraint function and fail when a constraint test fails
        for constraint in self.constraints:
            if not constraint(partition):
                return False

        # all constraints are satisfied
        return True


class Bounds:
    """
    Wrapper for numeric-validators to enforce upper and lower limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within set limits, and
    ``False`` otherwise.

    """
    def __init__(self, func, bounds):
        """
        :func: Numeric validator function. Should return an iterable of values.
        :bounds: Tuple of (lower, upper) numeric bounds.
        """
        self.func = func
        self.bounds = bounds

    def __call__(self, *args, **kwargs):
        lower, upper = self.bounds
        values = self.func(*args, **kwargs)
        return lower <= min(values) and max(values) <= upper

    @property
    def __name__(self):
        """TODO: Docstring for __name__.
        :returns: TODO

        """
        return "Bounds({})".format(self.func.__name__)


class UpperBound:
    """
    Wrapper for numeric-validators to enforce upper limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set upper limit,
    and ``False`` otherwise.

    """
    def __init__(self, func, bound):
        """
        :func: Numeric validator function. Should return a comparable value.
        :bounds: Comparable upper bound.
        """
        self.func = func
        self.bound = bound

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs) <= self.bound


class LowerBound:
    """
    Wrapper for numeric-validators to enforce lower limits.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set lower limit,
    and ``False`` otherwise.

    """
    def __init__(self, func, bound):
        """
        :func: Numeric validator function. Should return a comparable value.
        :bounds: Comparable lower bound.
        """
        self.func = func
        self.bound = bound

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs) >= self.bound


class SelfConfiguringUpperBound:
    """
    Wrapper for numeric-validators to enforce automatic upper limits.

    When instantiated, the initial upper bound is set as the initial value of
    the numeric-validator.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set upper limit,
    and ``False`` otherwise.

    """
    def __init__(self, func):
        """
        :func: Numeric validator function.
        """
        self.func = func
        self.bound = None

    def __call__(self, partition):
        if not self.bound:
            self.bound = self.func(partition)
            return self.__call__(partition)
        else:
            return self.func(partition) <= self.bound


class SelfConfiguringLowerBound:
    """
    Wrapper for numeric-validators to enforce automatic lower limits.

    When instantiated, the initial lower bound is set as the initial value of
    the numeric-validator minus some configurable ε.

    This class is meant to be called as a function after instantiation; its
    return is ``True`` if the numeric validator is within a set lower limit,
    and ``False`` otherwise.

    """
    def __init__(self, func, epsilon=0.05):
        """
        :func: Numeric validator function.
        :epsilon: Initial "wiggle room" that the validator allows.
        """
        self.func = func
        self.bound = None
        self.epsilon = epsilon

    def __call__(self, partition):
        if not self.bound:
            self.bound = self.func(partition) - self.epsilon
            return self.__call__(partition)
        else:
            return self.func(partition) >= self.bound


class WithinPercentRangeOfBounds:
    def __init__(self, func, percent):
        self.func = func
        self.percent = float(percent) / 100.
        self.lbound = None
        self.ubound = None

    def __call__(self, partition):
        if not (self.lbound and self.ubound):
            self.lbound = self.func(partition) * (1.0 - self.percent)
            self.ubound = self.func(partition) * (1.0 + self.percent)
            return True
        else:
            return self.lbound <= self.func(partition) <= self.ubound


def L1_reciprocal_polsby_popper(partition):
    return sum(1 / value for value in partition['polsby_popper'].values())


def L_minus_1_polsby_popper(partition):
    return len(partition.parts) / sum(1 / value for value in partition['polsby_popper'].values())


no_worse_L_minus_1_polsby_popper = SelfConfiguringLowerBound(L_minus_1_polsby_popper)

no_worse_L1_reciprocal_polsby_popper = SelfConfiguringUpperBound(L1_reciprocal_polsby_popper)


def L1_reciprocal_discrete_polsby_popper(partition):
    return sum(1 / value for value in partition['discrete_polsby_popper'].values())


def within_percent_of_ideal_population(initial_partition, percent=0.01):
    """
    Require that all districts are within a certain percent of "ideal" (i.e.,
    uniform) population.

    Ideal population is defined as "total population / number of districts."

    :initial_partition: Starting partition from which to compute district information.
    :percent: Allowed percentage deviation.
    :returns: A :class:`.Bounds` instance.

    """
    def population(partition):
        return partition["population"].values()

    number_of_districts = len(initial_partition['population'].keys())
    total_population = sum(initial_partition['population'].values())
    ideal_population = total_population / number_of_districts
    bounds = ((1 - percent) * ideal_population, (1 + percent) * ideal_population)

    return Bounds(population, bounds=bounds)


def single_flip_contiguous(partition):
    """
    Check if swapping the given node from its old assignment disconnects the
    old assignment class.

    :parition: Current :class:`.Partition` object.

    :flips: Dictionary of proposed flips, with `(nodeid: new_assignment)`
            pairs. If `flips` is `None`, then fallback to the
            :func:`.contiguous` check.

    :returns: True if contiguous, and False otherwise.

    We assume that `removed_node` belonged to an assignment class that formed a
    connected subgraph. To see if its removal left the subgraph connected, we
    check that the neighbors of the removed node are still connected through
    the changed graph.

    """
    parent = partition.parent
    flips = partition.flips
    if not flips or not parent:
        return contiguous(partition)

    graph = partition.graph
    assignment_dict = parent.assignment

    def proposed_assignment(node):
        """Return the proposed assignment of the given node."""
        if node in flips:
            return flips[node]

        return assignment_dict[node]

    def partition_edge_weight(start_node, end_node, edge_attrs):
        """
        Compute the district edge weight, which is 1 if the nodes have the same
        assignment, and infinity otherwise.
        """
        if proposed_assignment(start_node) != proposed_assignment(end_node):
            return float("inf")

        return 1

    for changed_node, _ in flips.items():
        old_neighbors = []
        old_assignment = assignment_dict[changed_node]

        for node in graph.neighbors(changed_node):
            if proposed_assignment(node) == old_assignment:
                old_neighbors.append(node)

        if not old_neighbors:
            # Under our assumptions, if there are no old neighbors, then the
            # old_assignment district has vanished. It is trivially connected.
            return True

        start_neighbor = random.choice(old_neighbors)

        for neighbor in old_neighbors:
            try:
                distance, _ = nx_path.single_source_dijkstra(graph, start_neighbor, neighbor,
                                                             weight=partition_edge_weight)
                if not (distance < float("inf")):
                    return False
            except NetworkXNoPath:
                return False

    # All neighbors of all changed nodes are connected, so the new graph is
    # connected.
    return True


def contiguous(partition):
    """Check if the assignment blocks of a partition are connected.

    :parition: :class:`rundmcmc.partition.Partition` instance.
    :flips: Dictionary of proposed flips, with `(nodeid: new_assignment)`
            pairs. If `flips` is `None`, then fallback :func:`.contiguous`.

    :returns: True if contiguous, False otherwise.

    """
    flips = partition.flips
    if not flips:
        flips = dict()

    def proposed_assignment(node):
        """Return the proposed assignment of the given node."""
        return partition.assignment[node]
    # TODO

    # Creates a dictionary where the key is the district and the value is
    # a list of VTDs that belong to that district
    district_dict = {}
    # TODO
    for node in partition.graph.nodes:
        # TODO
        dist = proposed_assignment(node)
        if dist in district_dict:
            district_dict[dist].append(node)
        else:
            district_dict[dist] = [node]

    # Checks if the subgraph of all districts are connected(contiguous)
    for key in district_dict:
        # TODO
        tmp = partition.graph.subgraph(district_dict[key])
        if nx.is_connected(tmp) is False:
            return False

    return True


def fast_connected(partition):
    """
    Checks that a given partition's components are connected using a simple breadth-first search.

    :partition: Instance of Partition; contains connected components.
    :returns: Boolean; Are the components of this partition connected?

    """
    assignment = partition.assignment

    # Inverts the assignment dictionary so that lists of VTDs are keyed
    # by their congressional districts.
    districts = collections.defaultdict(set)

    for vtd in assignment:
        districts[assignment[vtd]].add(vtd)

    # Generates a subgraph for each district and perform a BFS on it
    # to check connectedness.
    for district in districts:
        adj = nx.to_dict_of_lists(partition.graph, districts[district])
        if _bfs(adj) is False:
            return False

    return True


def non_bool_fast_connected(partition):
    """
    Return the number of non-connected assignment subgraphs.

    :partition: Instance of Partition; contains connected components.
    :return: int: number of contiguous districts
    """
    assignment = partition.assignment

    # Inverts the assignment dictionary so that lists of VTDs are keyed
    # by their congressional districts.
    districts = collections.defaultdict(set)
    returns = 0

    for vtd in assignment:
        districts[assignment[vtd]].add(vtd)

    # Generates a subgraph for each district and perform a BFS on it
    # to check connectedness.
    for district in districts:
        adj = nx.to_dict_of_lists(partition.graph, districts[district])
        if _bfs(adj):
            returns += 1

    return returns


no_more_disconnected = SelfConfiguringLowerBound(non_bool_fast_connected)


def _bfs(graph):
    """
    Performs a breadth-first search on the provided graph and returns true or
    false depending on whether the graph is connected.

    :graph: Dict-of-lists; an adjacency matrix.
    :returns: Boolean; is this graph connected?

    """
    q = [next(iter(graph))]
    visited = set()
    total_vertices = len(list(graph.keys()))

    # Check if the district has a single vertex. If it does, then simply return
    # `True`, as it's trivially connected.
    if total_vertices <= 1:
        return True

    # bfs!
    while len(q) is not 0:
        current = q.pop(0)
        neighbors = graph[current]

        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                q += [neighbor]

    return total_vertices == len(visited)


def districts_within_tolerance(partition, attribute_name="population", percentage=0.1):
    """
    Check if all districts are within a certain percentage of the "smallest"
    district, as defined by the given attribute.

    :partition: partition class instance
    :attrName: string that is the name of an updater in partition
    :percentage: what percent difference is allowed
    :return: boolean of if the districts are within specified tolerance

    """
    if percentage >= 1:
        percentage *= 0.01

    values = partition[attribute_name].values()
    max_difference = max(values) - min(values)

    within_tolerance = max_difference <= percentage * min(values)
    return within_tolerance


def population_balance(partition, attribute_name="population"):
    """
    Compute the ratio "range / minimum value" of the given attribute on
    assignment blocks.
    """
    values = partition[attribute_name].values()
    max_difference = max(values) - min(values)
    return max_difference / min(values)


def refuse_new_splits(partition_county_field):
    """Refuse all proposals that split a county that was previous unsplit.

    :partition_county_field: Name of field for county information generated by
                             :func:`.county_splits`.

    """
    def _refuse_new_splits(partition):
        for county_info in partition[partition_county_field].values():
            if county_info.split == CountySplit.NEW_SPLIT:
                return False

        return True

    return _refuse_new_splits


def no_vanishing_districts(partition):
    """Require that no districts be completely consumed."""
    if not partition.parent:
        return True
    return len(partition) == len(partition.parent)
