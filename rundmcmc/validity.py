import networkx as nx
import pandas as pd


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


def contiguous(partition):
    '''

    :graphObj: The graph object you are working on.
    :assignment: The assignment dictionary

    :return: A list of booleans to state if the sub graph is connected.
    '''

    # TODO

    # Creates a dictionary where the key is the district and the value is
    # a list of VTDs that belong to that district
    district_list = {}
    # TODO
    for node in partition.graph.nodes:
        # TODO
        dist = partition.assignment[node]
        if dist in district_list:
            district_list[dist].append(node)
        else:
            district_list[dist] = [node]

    # Checks if the subgraph of all districts are connected(contiguous)
    for key in district_list:
        # TODO
        tmp = partition.graph.subgraph(district_list[key])
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
