# -*- coding: utf-8 -*-
"""
Created on Wed Jun 27 10:41:37 2018

@author: Assaf, Lorenzo, Anthony
"""
from itertools import product
import numpy as np
import numpy as np

from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection

#from sklearn import manifold
#from sklearn.metrics import euclidean_distances
#from sklearn.decomposition import PCA


#from scipy.stats import gaussian_kde

def common_refinement(partition1, partition2):
    if set(partition1.keys()) != set(partition2.keys()):
        return "Keys do not match!"
    
    keys = partition1.keys()

    d = dict()
    i = 0
    coord_to_values_dict = dict()

    for assignment1, assignment2 in product(set(partition1.values()), set(partition2.values())):
        coord_to_values_dict[(assignmen1,assignment2)] = i
        i += 1 

    for node in keys:
        d[node] = (d1[node], d2[node])

    translated_dict = {node: coord_to_values_dict[d[node]] for node in keys}
    
    return translated_dict

def partition_entropy(partition):
    """Returns the entropy of a partition"""    
    number_of_units = len(partition)
    
    prob = {}
    
    for district_assignment in list(parition.values()):
        prob[district_assignment] = sum(1 for x in parition.keys() if partition[x] == district_assignment)/number_of_units
        
    H = sum(- prob[key] * np.log(prob[key]) for key in prob.keys())
    return H

def dict_invert(dictionary):
  dict = {val: [key for key in dictionary.keys() if dictionary[key] == val] for val in dictionary.values()}
  return dict

def find_closest_part(units_in_part, partition):
  parts = dict_invert(partition)
  min_symm_diff = len(units_in_part)
  
  for part_set in parts.values():
    symm_diff = set(part_set).symmetric_difference(set(units_in_part))
    print(min_symm_diff)
    if len(symm_diff) < min_symm_diff:
      min_symm_diff = len(symm_diff)
  return(min_symm_diff)

def shared_information_distance(partition1, partition2):
  return(2*partition_entropy(common_refinement(partition1,partition2)) - partition_entropy(partition1) - partition_entropy(partition2))

def stupid_hamming_pre_distance(partition1, partition2):
  parts1 = dict_invert(partition1)
  hamming_list = []
  for key in parts1.keys():
    hamming_list.append(find_closest_part(parts1[key], partition2))
  #print(hamming_list)
  return(sum(hamming_list))

def stupid_hamming_distance(partition1, partition2):
  return(stupid_hamming_pre_distance(partition1, partition2) + stupid_hamming_pre_distance(partition2, partition1))

def subgraph_list_to_dictionary(subgraph):
    m = len(subgraph)
    node_lists = [g.nodes() for g in subgraph]
    dictionary = {}
    for i in range(m):
        for x in node_lists[i]:
            dictionary[x] = i
    return dictionary

def partition_list_to_dictionary_list(partitions):
    dictionary_list = []
    for x in partitions:
        dictionary_list.append(subgraph_list_to_dictionary(x))
    return dictionary_list

def lp_distance(p1, p2, p):
    if set(p1.keys()) != set(p2.keys()):
        return "Keys do not match!"
    
    keys = p1.keys()
    difference_vector = []
    for k in keys:
            difference_vector.append( p1[k] - p2[k])
    return np.linalg.norm(difference_vector, p)

def build_distance_matrix(partitions):
    #Partition should be stored as dictionaries 
    n = len(partitions)
    M = np.zeros([n,n])
    for i in range(n):
        for j in range(n):
            M[i][j] = shared_information_distance(partitions[i], partitions[j])
            #M[i][j] = stupid_hamming_distance(partitions[i], partitions[j])
    return M
