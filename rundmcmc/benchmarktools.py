# -*- coding: utf-8 -*-
"""
Created on Wed Jun 27 10:41:37 2018

@author: MGGG
"""

from itertools import product
import numpy as np
import numpy as np

from matplotlib.collections import LineCollection

from sklearn import manifold
from sklearn.metrics import euclidean_distances
from sklearn.decomposition import PCA


from scipy.stats import gaussian_kde
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
    
def lp_distance(p1, p2, p):
    if set(p1.keys()) != set(p2.keys()):
        return "Keys do not match!"
    
    keys = p1.keys()
    difference_vector = []
    for k in keys:
            difference_vector.append( p1[k] - p2[k])
    return np.linalg.norm(difference_vector, p)
        
    
def build_distance_matrix(partitions, metric = "information", p = 1):
    #Partition should be stored as dictionaries 
    n = len(partitions)
    M = np.zeros([n,n])
    for i in range(n):
        for j in range(n):
            if metric == "information":
                M[i][j] = mi_metric(partitions[i], partitions[j])
            if metric == "Lp":
                #p = 1 is hamming
                M[i][j] = lp_distance(partitions[i], partitions[j],p)
    return M
 
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


############################################################

##Multi-Dimensional scaling

def make_mds(A, M_A, h1, dim = 2):
    #A is the ground set of partitions
    #M_A is the distance matrix
    #h1 is the histogram (labeled by A_node_lists -- below) that tells us the heat map
    color_list = []
    A_node_lists = [ set([frozenset(g.nodes()) for g in x]) for x in A]
    for x in A_node_lists:
        color_list.append(h1[str(x)])
    z = gaussian_kde(color_list)(color_list)
    
    similariaties = M_A
    seed = np.random.RandomState(seed=3)
    
    mds = manifold.MDS(n_components=2, max_iter=3000, eps=1e-9, random_state=seed,
                       dissimilarity="precomputed", n_jobs=1)
    
    mds.fit(similariaties)
    pos = mds.embedding_
    # Rotate the data
    clf = PCA(n_components=2)    
    pos = clf.fit_transform(pos)
    
    s = 100
    
    from matplotlib import pyplot as plt
    plt.scatter(pos[:, 0], pos[:, 1], c=z, s=s, lw=0)    
    plt.show()
    
def stress_test(A, M_A, h1, low_dim = 2, high_dim = 10):
    stress_list = []
    similariaties = M_A
    seed = np.random.RandomState(seed=3)
    for k in range(low_dim, high_dim):
        mds = manifold.MDS(n_components=2, max_iter=3000, eps=1e-9, random_state=seed,
                           dissimilarity="precomputed", n_jobs=1)        
        mds.fit(similariaties)
        print(mds.stress_)
        stress_list.append(mds.stress_)
    from matplotlib import pyplot as plt
    plt.plot(stress_list)
    plt.show()
    
def testmds():
    #To see the stress function -- chcek out stress test. It doesn't seem to improve by increaseing dimension.
    #Probably this means that this space cannot be easily embedded. Maybe try hamming?
    from treetools import test
    h1, A, partitions = test([3,3], 3,1000)
    dlist_A = partition_list_to_dictionary_list(A)
    M_A = build_distance_matrix(dlist_A)
    make_mds(A, M_A, h1)
   # stress_test(A, M_A, h1, 2, 25)
    
testmds()
    
##########################################################
#Spectral Embeddings

def spectral_plot(A, M_A, h1, n = 2):
    
    color_list = []
    A_node_lists = [ set([frozenset(g.nodes()) for g in x]) for x in A]
    for x in A_node_lists:
        color_list.append(h1[str(x)])
    z = gaussian_kde(color_list)(color_list)
    
    se = manifold.SpectralEmbedding(n_components = 3, affinity = 'precomputed')
    Y = se.fit_transform(M_A)
    if n == 2:
        import matplotlib.pyplot as plt
        plt.scatter(Y[:, 0], Y[:, 1], c=z)
        plt.show()
    if n == 3:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        fig = plt.figure()
        ax = fig.add_subplot(111,projection='3d')
        ax.scatter(Y[:,0], Y[:,1], Y[:,2],  c = z)

def test_spectral():
    #it would be great to have a tool that lets us see which partitions are which by hovering over them
    from treetools import test
    h1, A, partitions = test([3,3], 3,50)
    dlist_A = partition_list_to_dictionary_list(A)
    M_A = build_distance_matrix(dlist_A)
    spectral_plot(A, M_A, h1, 3)

test_spectral() 
##Spectral partitioning

#K medioids