from networkx import NetworkXNoPath
import networkx.algorithms.shortest_paths.weighted as nx_path
import networkx as nx
import pandas as pd
import random


class Validator:
    def __init__(self, constraints):
        '''
        :constraints: The list of functions that will check to see if your assignment is valid
        '''
        self.constraints = constraints

    def __call__(self, partition):
        '''
        :graph: the networkx graph of vtds
        :dist_dict: the district assignment dictionary
        '''

        # check each constraint function and fail when a constraint test fails
        for constraint in self.constraints:
            if constraint(partition) is False:
                return False

        # all constraints are satisfied
        return True


def single_flip_contiguous(partition, flips=None):
    """
    Check if swapping the given node from its old assignment disconnects the
    old assignment class.

    :parition: Current :class:`.Partition` object.

    :flips: Dictionary of proposed flips, with `(nodeid: new_assignment)`
            pairs. If `flips` is `None`, then fallback to the
            :func:`.contiguous` check.

    :returns: Boolean.

    We assume that `removed_node` belonged to an assignment class that formed a
    connected subgraph. To see if its removal left the subgraph connected, we
    check that the neighbors of the removed node are still connected through
    the changed graph.

    """
    if not flips:
        return contiguous(partition, flips)

    graph = partition.graph
    assignment_dict = partition.assignment

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


def contiguous(partition, flips=None):
    '''

    :parition: Current :class:`.Partition` object.

    :flips: Dictionary of proposed flips, with `(nodeid: new_assignment)`
            pairs. If `flips` is `None`, then fallback to the
            :func:`.contiguous` check.

    :returns: True if contiguous, false otherwise.

    :return: A list of booleans to state if the sub graph is connected.
    '''
    if not flips:
        flips = dict()

    def proposed_assignment(node):
        """Return the proposed assignment of the given node."""
        if node in flips:
            return flips[node]

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

    # all districts are contiguous
    '''
    for district in partition.districts:
        if partition.districts[district]['contiguous'] is False:
            return False
    '''

    return True


# TODO make attrName and percentage configurable
def districts_within_tolerance(partition):
    """
    :graphObj: networkX graph object
    :attrName: string that is the name of a field in graphObj nodes (e.g. population)
    :assignment: dictionary with keys that are node ids and values of assigned district
    :percentage: what percent difference is allowed
    :return: boolean of if the districts are within specified tolerance
    """
    withinTol = False
    percentage = 0.01
    attrName = 'POP10'

    if percentage >= 1:
        percentage *= 0.01

    # get value of attrName column for each graph node
    # TODO fixe when partition class is implemented
    cdVals = [(partition.assignment[n], n[attrName]) for n in partition.graphObj.nodes(data=True)]
    # get sum of all nodes per district as found in assignment
    cdVals = pd.DataFrame(cdVals).groupby(0)[1].sum().tolist()
    # total difference in value between any two districts
    maxDiff = max(cdVals) - min(cdVals)
    # get percent of smallest district (in terms of attrName)
    percentage = percentage * min(cdVals)

    if maxDiff <= percentage:
        withinTol = True

    return withinTol
