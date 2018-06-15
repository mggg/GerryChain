import pandas as pd
from graph_tool import GraphView
from graph_tool.topology import label_components
import numpy as np


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

    _, dist_idxs = np.unique(partition.graph.vp.CD.a, return_index=True)
    dists = partition.graph.vp.CD.a[dist_idxs]

    for i in dists:
        vfilt = partition.graph.new_vertex_property('bool')
        vfilt = partition.graph.vp.CD.a == np.full(len(vfilt.a), i)
        tmp = GraphView(partition.graph, vfilt)
        _, hist = label_components(tmp)
        if len(hist) != 1:
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
