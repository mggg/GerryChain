# -*- coding: utf-8 -*-
"""
Created on Wed Jun 27 10:41:37 2018

@author: MGGG
"""

from itertools import product
import numpy as np
def common_refinement(d1,d2):
    if set(d1.keys()) != set(d2.keys()):
        return "Keys do not match!"
    
    keys = d1.keys()

    d = dict()
    i = 0
    coord_to_values_dict = dict()

    for value1, value2 in product(set(d1.values()), set(d2.values()) ):
        coord_to_values_dict[(value1,value2)] = i
        i += 1 


    for node in keys:
        d[node] = (d1[node], d2[node])

    translated_dict = {node: coord_to_values_dict[d[node]] for node in keys}
    
    return translated_dict

def partition_entropy(d):
    """Returns the entropy of a partition"""    
    total = len(d)
    
    prob = {}
    
    for value in list(d.values()):
        prob[value] = sum(1 for x in d.keys() if d[x] == value)/total
        
    H = sum(- prob[key] * np.log(prob[key]) for key in prob.keys())
    return H


def mutual_information(dX,dY):
    d = common_refinement(dX,dY)
    HX = partition_entropy(dX)
    HY = partition_entropy(dY)
    HXY = partition_entropy(d)
    
    I = HX + HY - HXY
    return I
    
def mi_metric(d1,d2, normalised = False):
    d = common_refinement(d1,d2)
    H = partition_entropy(d)
    I = mutual_information(d1,d2)
    
    if normalised is True:
        return (H-I)/H
    else:
        return H-I
    
def build_distance_matrix(partitions):
    n = len(partitions)
    M = np.zeros([n,n])
    for i in range(n):
        for j in range(n):
            M[i][j] = mi_metric(partitions[i], partitions[j])
    return M
 