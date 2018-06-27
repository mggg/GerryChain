# -*- coding: utf-8 -*-
"""
Created on Tue Jun 26 12:01:21 2018

@author: MGGG
"""

import networkx as nx
import random

import numpy as np
import scipy.linalg
from scipy.sparse import csc_matrix
import scipy
from scipy import array, linalg, dot
#from naive_graph_partitions import k_connected_graph_partitions

######Tree counting

def log_number_trees(G, weight = False):
    #Kirkoffs is the determinant of the minor..
    #at some point this should be replaced with a Cholesky decomposition based algorithm, which is supposedly faster. 
    if weight == False:
        m = nx.laplacian_matrix(G)[1:,1:]
    if weight == True:
        m = nx.laplacian_matrix(G, weight = "weight")[1:,1:]
    m = csc_matrix(m)
    splumatrix = scipy.sparse.linalg.splu(m)
    diag_L = np.diag(splumatrix.L.A)
    diag_U = np.diag(splumatrix.U.A)
    S_log_L = [np.log(s) for s in diag_L]
    S_log_U = [np.log(s) for s in diag_U]
    LU_prod = np.sum(S_log_U) + np.sum(S_log_L)
    return  LU_prod


def score_tree_edges_pair(G,T,e):
    partition = R(G,T,e)
    tree_term = np.sum([log_number_trees(g) for g in partition])

    #Use the weighted version of Kirkoffs theorem-- weight each edge by the number of cut edges
    #I.e. build the adjacency graph of the partition, weight by cut size
    #This counts the number of ways to extend spanning trees on the subgraphs of the parittion
    #individually, to a spanning tree on all of G
    connector_graph = nx.Graph()
    connector_graph.add_nodes_from(partition)
    for x in partition:
        for y in partition:
            if x != y:
                cutedges = cut_edges(G, x,y)
                if cutedges != []:
                    connector_graph.add_edge(x,y, weight = len(cutedges))
    cut_weight = log_number_trees(connector_graph, True)
    return -1 * (tree_term + cut_weight)
    #YOU NEED THIS -1 -- the score is the inverse! Don't take it away!
    
#####For creating a spanning tree

def srw(G,a):
    wet = set([a])
    trip = [a]
    while len(wet) < len(G.nodes()):
        b = random.choice(list(G.neighbors(a)))
        wet.add(b)
        trip.append(b)
        a = b
    return trip

def forward_tree(G,a):
    walk = srw(G,a)
    edges = []
    for x in G.nodes():
        if (x != walk[0]):
            t = walk.index(x)
            edges.append( [walk[t], walk[t-1]])
    return edges

def random_spanning_tree(G):
    #It's going to be faster to use the David Wilson algorithm here instead.
    T_edges = forward_tree(G, random.choice(list(G.nodes())))
    T = nx.Graph()
    T.add_nodes_from(list(G.nodes()))
    T.add_edges_from(T_edges)
    return T

#####For lifting:

def cut_edges(G, G_A,G_B):
    #Finds the edges in G from G_A to G_B
    

    edges_of_G = list(G.edges())

    list_of_cut_edges = []
    for e in edges_of_G:
        if e[0] in G_A and e[1] in G_B:
            list_of_cut_edges.append(e)
        if e[0] in G_B and e[1] in G_A:
            list_of_cut_edges.append(e)
    return list_of_cut_edges

def random_lift(G, subgraphs):
    number_of_parts = len(subgraphs)
    trees = [random_spanning_tree(g) for g in subgraphs]
    
    #This builds a graph with nodes the subgraph, and they are connected
    #if there is an edge connecting the two subgraphs
    #and each edge gets 'choices' = to all the edges in G that connect the two subgraphs
    connector_graph = nx.Graph()
    connector_graph.add_nodes_from(subgraphs)
    for x in subgraphs:
        for y in subgraphs:
            if x != y:
                cutedges = cut_edges(G, x,y)
                if cutedges != []:
                    connector_graph.add_edge(x,y, choices = cutedges)
                    #need to worry about directendess!!???
                    
                    
    connector_meta_tree = random_spanning_tree(connector_graph)
    connector_tree = nx.Graph()
    for e in connector_meta_tree.edges():
        w = random.choice(connector_graph[e[0]][e[1]]['choices'])
        connector_tree.add_edges_from([w])
        
    
    T = nx.Graph()
    for x in trees:
        T.add_edges_from(x.edges())
    T.add_edges_from(connector_tree.edges())
    e = random.sample(list(T.edges()),number_of_parts - 1)
    return [T,e]

######Projection tools:
    
def R(G,T,edge_list):
    T.remove_edges_from(edge_list)
    components = list(nx.connected_components(T))
    T.add_edges_from(edge_list)
    subgraphs = [nx.induced_subgraph(G, A) for A in components]
    return subgraphs
#
#def best_edge_for_equipartition(G,T):
#    list_of_edges = list(T.edges())
#    best = 0
#    candidate = 0
#    for e in list_of_edges:
#        score = equi_score_tree_edge_pair(G,T,e)
#        if score > best:
#            best = score
#            candidate = e
#    return [candidate, best]
#
#def equi_score_tree_edge_pair(G,T,e):
#    T.remove_edges_from([e])
#    components = list(nx.connected_components(T))
#    T.add_edges_from([e])
#    A = len(components[0])
#    B = len(components[1])
#    x =  np.min([A / (A + B), B / (A + B)])
#    return x

###Metropolis-Hastings tools
    
def propose_step(G,T):
    T_edges = list(T.edges())
    T_edges_t = [ tuple((e[1], e[0])) for e in T_edges]
    #Because of stupid stuff in networkx
    A = [e for e in G.edges() if e not in T_edges and e not in T_edges_t]
    e = random.choice(A)
    T.add_edges_from([e])
    C = nx.find_cycle(T, orientation = 'ignore')
    w = random.choice(C)
    U = nx.Graph()
    U.add_edges_from(list(T.edges()))
    U.remove_edges_from([w])
    T.remove_edges_from([e])
#    print(len(U.edges()))
#    print(U.edges())
    return U
    


def MH_step(G, T,e):
    n = len(e)
    U = propose_step(G,T)
    e2 = random.sample(list(U.edges()), n)
    current_score = score_tree_edges_pair(G,T,e)
    new_score = score_tree_edges_pair(G, U, e2)
    if new_score > current_score:
        return [U,e2]
    else:
       p = np.exp(new_score - current_score)
       a = np.random.uniform(0,1)
       if a < p:
           return [U,e2]
       else:
           return [T,e]

        
########Validation -- 
            
def count(x, visited_partitions):

    x_lens = np.sort([len(k) for k in x])
    count = 0
    for i in visited_partitions:
        sample_nodes = set([frozenset(g.nodes()) for g in i])
        sample_lens = np.sort([len(k) for k in sample_nodes])
        #if (x_lens == sample_lens).all():
        if np.array_equal(x_lens , sample_lens):
            if x == sample_nodes:
                count += 1
    return count

def make_histogram(A, visited_partitions):
    A_node_lists = [ set([frozenset(g.nodes()) for g in x]) for x in A]
    dictionary = {}
    for x in A_node_lists:
        dictionary[str(x)] = count(x,visited_partitions) / len(visited_partitions)
    return dictionary
        
def test(grid_size, k_part, steps = 100):
    from naive_graph_partitions import k_connected_graph_partitions
    #k_part = 3
    G = nx.grid_graph(grid_size)
    A = list(k_connected_graph_partitions(G, k_part))
    T = random_spanning_tree(G)
    e = list(T.edges())[0:k_part - 1]
    visited_partitions = []
    for i in range(100):
        new = MH_step(G, T, e)
        T = new[0]
        e = new[1]
        visited_partitions.append(R(G,T,e))
    histogram = make_histogram(A, visited_partitions)
    total_variation = 0
    for k in histogram.keys():
        total_variation += np.abs( histogram[k] - 1 / len(A))
    print("total variation", total_variation)
    return [histogram, A, visited_partitions]
     
def TV(p,q):
    total_variation = 0
    for k in p.keys():
        total_variation += np.abs(p[k] - q[k])
    return total_variation
h1, A, partitions = test([2,3], 3)
