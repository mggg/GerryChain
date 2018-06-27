# -*- coding: utf-8 -*-
"""
Created on Wed Jun 27 10:41:37 2018

@author: MGGG
"""

from itertools import product
import numpy as np


def common_refinement(d1, d2):
    if set(d1.keys()) != set(d2.keys()):
        return "Keys do not match!"

    keys = d1.keys()

    d = dict()
    i = 0
    coord_to_values_dict = dict()

    for value1, value2 in product(set(d1.values()), set(d2.values())):
        coord_to_values_dict[(value1, value2)] = i
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
        prob[value] = sum(1 for x in d.keys() if d[x] == value) / total

    H = sum(- prob[key] * np.log(prob[key]) for key in prob.keys())
    return H


def mutual_information(dX, dY):
    d = common_refinement(dX, dY)
    HX = partition_entropy(dX)
    HY = partition_entropy(dY)
    HXY = partition_entropy(d)

    I = HX + HY - HXY
    return I


def mi_metric(d1, d2, normalised=False):
    d = common_refinement(d1, d2)
    H = partition_entropy(d)

    I = mutual_information(d1, d2)

    if normalised is True:
        return (H - I) / H
    else:
        return H - I


def build_distance_matrix(partitions):
    # Partition should be stored as dictionaries
    n = len(partitions)
    M = np.zeros([n, n])
    for i in range(n):
        for j in range(n):
            M[i][j] = mi_metric(partitions[i], partitions[j])
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


from treetools import test

h1, A, partitions = test([3, 2], 3, 1000)
d = subgraph_list_to_dictionary(partitions[0])
dlist_A = partition_list_to_dictionary_list(A)
dlist_partitions = partition_list_to_dictionary_list(partitions)
M_A = build_distance_matrix(dlist_A)
M_Sample = build_distance_matrix(dlist_partitions)

color_list = []
A_node_lists = [set([frozenset(g.nodes()) for g in x]) for x in A]
for x in A_node_lists:
    color_list.append(h1[str(x)])

from scipy.stats import gaussian_kde

z = gaussian_kde(color_list)(color_list)
############################################################

##Multi-Dimensional scaling

print(__doc__)
import numpy as np

from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection

from sklearn import manifold
from sklearn.metrics import euclidean_distances
from sklearn.decomposition import PCA

similariaties = M_A

seed = np.random.RandomState(seed=3)

mds = manifold.MDS(n_components=2, max_iter=3000, eps=1e-9, random_state=seed,
                   dissimilarity="precomputed", n_jobs=1)

pos = mds.fit(similariaties).embedding_
# npos = mds.fit(similariaties_A).embedding_


# Rotate the data
clf = PCA(n_components=2)

pos = clf.fit_transform(pos)

fig = plt.figure(1)
ax = plt.axes([0., 0., 1., 1.])

s = 100
plt.scatter(pos[:, 0], pos[:, 1], c=z, s=s, lw=0, label='MDS')
plt.legend(scatterpoints=1, loc='best', shadow=False)

plt.show()

##########################################################
# Spectral Embeddings

##Spectral partitioning

# K medioids
