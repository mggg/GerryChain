import networkx as nx
import pandas as pd


def contiguous(graph):
    '''

    :param graph: The graph object you are working on.
    :return: A list of booleans to state if the sub graph is connected.
    '''
    # Creates a dictionary where the key is the district and the value is
    # a list of VTDs that belong to that district
    district_list = {}
    for nodes in graph.nodes.data('CD'):
        dist = int(nodes[1])
        if dist in district_list:
            district_list[dist].append(nodes[0])
        else:
            district_list[dist] = [nodes[0]]

    # Checks if the subgraph of one district is connected(contiguous)
    dist_contig = []
    for key in district_list:
        tmp = graph.subgraph(district_list[key])
        dist_contig.append(nx.is_connected(tmp))
    return dist_contig


def districts_within_tolerance(graphObj, attrName, assignment, percentage):
    """
    :graphObj: networkX graph object 
    :attrName: string that is the name of a field in graphObj nodes (e.g. population)
    :assignment: dictionary with keys that are node ids and values of assigned district
    :percentage: what percent difference is allowed
    :return: boolean of if the districts are within specified tolerance
    """
    withinTol = False

    if percentage >= 1:
        percentage *= 0.01

    # get value of attrName column for each graph node
    cdVals = [(assignment[n], n[attrName]) for n in graphObj.nodes(data=True)]
    # get sum of all nodes per district as found in assignment
    cdVals = pd.DataFrame(cdVals).groupby(0)[1].sum().tolist()
    # total difference in value between any two districts
    maxDiff = max(cdVals) - min(cdVals)
    # get percent of smallest district (in terms of attrName)
    percentage = percentage * min(cdVals)

    if maxDiff <= percentage:
        withinTol = True

    return withinTol
