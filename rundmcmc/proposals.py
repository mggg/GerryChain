import random


# def propose_any_node_flip(partition):
#     """Propose to pick a random node to a
#     random part

#     """

#     node = random.choice(tuple(partition.assignment.keys()))
#     newpart = random.choice(tuple(partition.assignment.values()))

#     return {node: newpart}


# def propose_random_flip_with_loops(partition):
#     """Proposes a random boundary flip from the partition.
#     Uses the number of cut edges to determine self--loops.

#     :partition: The current partition to propose a flip from.
#     :returns: a dictionary with the flipped node mapped to its new assignment

#     """
#     # self loop
#     numEdges = 2.0 * len(partition['cut_edges'])
#     if random.random() < 1.0 - (numEdges * 1.0 / partition.max_edge_cuts):
#         return dict()

#     flip = propose_random_flip(partition)

#     # checks for a frozen nodes field and self loops if the value has
#     # been set to 1
#     flipped_node = list(flip.keys())[0]
#     node_attrs = partition.graph.nodes[flipped_node]
#     if "Frozen" in node_attrs and node_attrs["Frozen"]:
#         return dict()

#     return flip


# def propose_random_flip_metagraph(partition):
#     """Proposes a random boundary flip from the partition.
#     Uses the metagraph degree to determine self--loops.
#     Very slow.

#     :partition: The current partition to propose a flip from.
#     :returns: a dictionary with the flipped node mapped to its new assignment

#     """
#     # self loop
#     numEdges = partition["metagraph_degree"]
#     if random.random() < 1.0 - (numEdges * 1.0 / partition.max_edge_cuts):
#         return dict()

#     flip = propose_random_flip(partition)

#     # checks for a frozen nodes field and self loops if the value has
#     # been set to 1
#     flipped_node = list(flip.keys())[0]
#     node_attrs = partition.graph.nodes[flipped_node]
#     if "Frozen" in node_attrs and node_attrs["Frozen"]:
#         return dict()

#     return flip


# def propose_several_random_flips(partition):
#     """Proposes between 2 and 7 random boundary flips from the partition.
#        Calls the propose_random_flip() method from this file.

#     :partition: The current partition to propose a flip from.
#     :returns: a dictionary with the flipped nodes mapped to their new assignments

#     """
#     number_of_flips = random.randint(2, 7)

#     proposal = dict()

#     for i in range(number_of_flips):
#         proposal.update(propose_random_flip(partition))

#     return proposal


# def propose_flip_every_district(partition):
#     """Proposes a random boundary flip for each district in the partition.

#     :partition: The current partition to propose a flip from.
#     :returns: a dictionary with the flipped nodes mapped to their new assignments

#     """
#     proposal = dict()

#     for dist_edges in partition['cut_edges_by_part'].values():
#         edge = random.choice(list(dist_edges))

#         index = random.choice((0, 1))
#         flipped_node, other_node = edge[index], edge[1 - index]
#         flip = {flipped_node: partition.assignment[other_node]}

#         proposal.update(flip)

#     return proposal


# def propose_chunk_flip(partition):
#     """Chooses a random boundary node and proposes to flip it and all of its neighbors

#     :partition: The current partition to propose a flip from.
#     :returns: a dictionary with the flipped nodes mapped to their new assignments

#     """
#     proposal = dict()

#     edge = random.choice(tuple(partition['cut_edges']))
#     index = random.choice((0, 1))

#     flipped_node = edge[index]

#     valid_flips = [nbr for nbr in partition.graph.neighbors(
#         flipped_node) if partition.assignment[nbr] != partition.assignment[flipped_node]]

#     for flipped_neighbor in valid_flips:
#         proposal.update({flipped_neighbor: partition.assignment[flipped_node]})

#     return proposal


# def propose_flip_every_edge_of_district(partition):
#     """Chooses a random district to manipulate. Each edge on the boundary is
#        incident to a node in this district and a node outside of it. For each
#        edge, toss a fair coin. If tails, do nothing. If heads, toss a second
#        fair coin. If heads, add the node outside of this district to it. If
#        tails, add the node inside of this district to the other one.

#     :partition: The current partition to propose a flip from.
#     :returns: a dictionary with the flipped nodes mapped to their new assignments

#     """
#     proposal = dict()

#     edges = random.choice(list(partition['cut_edges_by_part'].values()))

#     for edge in edges:
#         if(random.random() > .5):
#             index = random.choice((0, 1))
#             flipped_node, other_node = edge[index], edge[1 - index]
#             proposal.update({flipped_node: partition.assignment[other_node]})

#     return proposal


# def propose_single_or_chunk(partition):
#     """With probability .9, chooses a random boundary node and proposes to flip it.
#        With probability .1, chooses a random boundary node and proposes to flip it
#        and all of its neighbors.
#        Calls the propose_random_flip() and propose_chunk_flip()
#        methods from this file.


#     :partition: The current partition to propose a flip from.
#     :returns: a dictionary with the flipped nodes mapped to their new assignments

#     """
#     if(random.random() > .1):
#         return propose_random_flip(partition)
#     else:
#         return propose_chunk_flip(partition)


# def number_of_flips(partition, dict_of_flips, prev_partition):
#     flips = partition.flips
#     if flips is None or flips is prev_partition:
#         return dict_of_flips, prev_partition
#     else:
#         prev_partition = flips
#         dict_of_flips[next(iter(flips))] = dict_of_flips.get(next(iter(flips)), 0) + 1
#         return dict_of_flips, prev_partition


def propose_random_flip(partition):
    """Proposes a random boundary flip from the partition.

    :partition: The current partition to propose a flip from.
    :returns: a dictionary with the flipped node mapped to its new assignment

    """
    edge = random.choice(tuple(partition['cut_edges']))
    index = random.choice((0, 1))

    flipped_node, other_node = edge[index], edge[1 - index]

    flip = {flipped_node: partition.assignment[other_node]}

    return flip


# def propose_lowest_pop_single_flip(partition):
#     dists = list(partition['population'])
#     pops = partition['population'].values()
#     rev_pop = dict(zip(pops, dists))
#     dist = rev_pop[min(pops)]

#     edge = random.choice(tuple(partition['cut_edges_by_part'][dist]))

#     if partition.assignment[edge[0]] == dist:
#         flip = {edge[1]: dist}
#     else:
#         flip = {edge[0]: dist}

#     return flip


# def propose_single_lowest_pop_or_random(partition):
#     if(random.random() > .2):
#         return propose_random_flip(partition)
#     else:
#         return propose_lowest_pop_single_flip(partition)


# def propose_chunk_swap(partition):
#     proposal = dict()
#     dists = list(partition.parts)

#     while len(dists) != 0:
#         dist = dists[0]

#         edge = random.choice(list(partition['cut_edges_by_part'][dist]))
#         index = random.choice((0, 1))
#         flipped_node = edge[index]

#         if partition.assignment[flipped_node] != dist:
#             proposal[flipped_node] = dist

#         valid_flips = []
#         count = 0

#         for nbr in partition.graph.neighbors(flipped_node):
#             if len(valid_flips) == 0:
#                 if partition.assignment[nbr] != dist:
#                     valid_flips.append(nbr)
#                     count = count + 1

#             else:
#                 a = partition.assignment[valid_flips[0]]
#                 if a == partition.assignment[nbr]:
#                     valid_flips.append(nbr)
#                     count = count + 1

#         for flipped_neighbor in valid_flips:
#             proposal[flipped_neighbor] = dist

#         dists.remove(dist)

#     return proposal


# def reversible_chunk_flip(partition):
#     edge = random.choice(tuple(partition['cut_edges']))
#     index = random.choice((0, 1))

#     flipped_node, other_node = edge[index], edge[1 - index]
#     flip_to = partition.assignment[flipped_node]
#     flip_from = partition.assignment[other_node]

#     num_flips = 1
#     flips = [flipped_node]
#     choices = [nbr for nbr in partition.graph.neighbors(flipped_node)
#                if partition.assignment[nbr] == flip_from]
#     while(choices and random.random() < .5 ** num_flips):
#         next_flip = random.choice(tuple(choices))
#         flips.append(next_flip)
#         num_flips += 1
#         choices.remove(next_flip)
#         new_choices = [nbr for nbr in partition.graph.neighbors(next_flip)
#                        if partition.assignment[nbr] == flip_from and nbr not in flips]
#         choices = list(set(choices) | set(new_choices))
#     return {flip: flip_to for flip in flips}


def max_edge_cuts(partition):
    """returns wes computation for max number of edge cuts... not well documented,
    and a vague upper bound (to be made smaller if possible)

    inputs:
    :partition: a partition instance.

    returns: an integer value

    """
    # TODO need number of frozen edges of graph
    numFrozen = 0
    numDists = len(partition)
    return 2 * (2 * len(partition.graph.nodes) + (numDists - numFrozen) - 6)
