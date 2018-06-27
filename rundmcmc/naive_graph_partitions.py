# -*- coding: utf-8 -*-
"""
Created on Mon Jun 11 10:28:05 2018

@author: Patrick Girardet 
Generates partitions of sets and graphs via simple combinatorial enumeration. 
"""

import networkx as nx
import itertools
import copy

# Enumerates the set partitions of an input list. If the length of the input
# list is n, this should generate B_n (the nth Bell number) partitions.
# Input: a_list - a Python list

def list_partitions(a_list):
    # Cast in case the input is something like a dataframe instead of a list.
    a_list = list(a_list)
    if len(a_list) < 1:
        yield []
    elif len(a_list) == 1:
        yield [a_list]
    else:
        for k in range(len(a_list)): 
          for subset in itertools.combinations(a_list[1:], k):
                first_subset = list(subset)
                first_subset.append(a_list[0])
                remainder_list = [elt for elt in a_list if elt not in first_subset]
                if len(remainder_list) == 0:
                    yield [first_subset]
                else:
                    for recursive_partition in list_partitions(remainder_list):
                        partition = [first_subset]
                        partition.extend(recursive_partition)
                        yield partition
    
# Enumerates the set partitions with k subsets of an input list. If the lengthe
# of the input list is n, this should generate S(n,k) partitions, the Stirling
# numbers of the second kind.
# Input: a_list - a Python list
# Input: k - the number of desired subsets in the partition. Should have k >= 0.
def k_list_partitions(a_list, k):
    # Cast in case the input is something like a dataframe instead of a list.
    a_list = list(a_list)
    n = len(a_list)
    if k > n:
        print("Invalid input: had k > n. Returning null partition.")
        yield []
    elif n < 0 or k < 0:
        print("Invalid input: either n < 0 or k < 0. Returning null partition.")
        yield []
    # Hardcoding of edge values.
    elif k == 0:
        if n == 0:
            yield [[]]
        else:
            yield []
    elif k == 1:
        yield [a_list]
    elif n == k:
        yield [[elt] for elt in a_list]
    # Uses standard recursion S(n,k) = k*S(n-1,k) + S(n-1,k-1) - first element
    # can either be a singleton for S(n-1,k-1) partitions, or can be placed into
    # one of k other sets for k*S(n-1,k) partitions.
    else:
        for partition in k_list_partitions(a_list[1:], k-1):
            # Put in first element as singleton set.
            partition.append([a_list[0]])
            yield partition
        for partition in k_list_partitions(a_list[1:], k):
            # Put first element into another subset.
            for subset in partition:
                subset.append(a_list[0])
                yield copy.deepcopy(partition)
                subset.remove(a_list[0])

# A dynamic programming implementation of the k_list_partitions function. NOTE:
# This function tends to be slower than the naive implementation for some reason.
# Stick to using k_list_partitions unless this is successfully optimized.
# Input: a_list - a Python list
# Input: k - the number of sets to appear in each partition
def dynamic_k_list(a_list, k):
    n = len(a_list)
    # Storage array for dynamic programming.
    partitions = [[[[]] for j in range(n+1)] for i in range(n+1)]
    # Base cases
    partitions[0][0] = [[]]
    for i in range(1, n+1):
        partitions[i][0] = []
    for i in range(1, n+1):
        partitions[i][1] = [[a_list[:i]]]
    for i in range(2, n+1):
        partitions[i][i] = [[[elt] for elt in a_list[:i]]]
    for i in range(1, n+1):
        for j in range(2, min(k+1,i+1)):
            if i == j or i == n and j == k:
                continue
            else:
                # First create the partitions obtained by adding a_list[i-1] as
                # a singleton set.
                singleton_partitions = []
                for partition in partitions[i-1][j-1]:
                    new_partition = copy.deepcopy(partition)
                    new_partition.append([a_list[i-1]])
                    singleton_partitions.append(new_partition)
                # Now create the partitions obtained by adding a_list[i-1] to
                # an existing set in the partition.
                inserted_partitions = []
                for partition in partitions[i-1][j]:
                    for subset in partition:
                        subset.append(a_list[i-1])
                        inserted_partitions.append(copy.deepcopy(partition)
                        subset.remove(a_list[i-1])
                partitions[i][j] = singleton_partitions
                partitions[i][j].extend(inserted_partitions)

    for partition in partitions[n-1][k-1]:
        new_partition = partition
        new_partition.append([a_list[k-1]])
        yield new_partition
        
    for partition in partitions[n-1][k]:
        for subset in partition:
            subset.append(a_list[n-1])
            yield copy.deepcopy(partition)
            subset.remove(a_list[n-1])
    
# Enumerates all possible partitions of a given graph.
# Input: G - a NetworkX graph
def graph_partitions(G):
    vertex_partitions = list_partitions(nx.nodes(G))
    for vertex_partition in vertex_partitions:
        graph_partition = []
        for subset in vertex_partition:
            subgraph = G.subgraph(subset)
            graph_partition.append(subgraph)
        yield graph_partition

# Enumerates all possible partitions of a given graph into connected subgraphs.
# Input: G - a NetworkX graph
def connected_graph_partitions(G):
    for partition in graph_partitions(G):
        valid = True
        for subgraph in partition:
            if not nx.is_connected(subgraph):
                valid = False
                break
        if not valid:
            continue
        else:
            yield partition

# Enumerates all possible partitions of a given graph into k subgraphs.
# Input: G - a NetworkX graph
def k_graph_partitions(G, k):
    vertex_partitions = k_list_partitions(nx.nodes(G), k)
    for vertex_partition in vertex_partitions:
        graph_partition = []
        for subset in vertex_partition:
            subgraph = G.subgraph(subset)
            graph_partition.append(subgraph)
        yield graph_partition

# Enumerates all possible partitions of a given graph into k connected subgraphs.
# Input: G - a NetworkX graph
def k_connected_graph_partitions(G, k):
    for partition in k_graph_partitions(G, k):
        valid = True
        for subgraph in partition:
            if not nx.is_connected(subgraph):
                valid = False
                break
        if not valid:
            continue
        else:
            yield partition
