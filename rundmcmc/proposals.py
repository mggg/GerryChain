import random


def propose_random_flip(partition):
    """Proposes a random boundary flip from the partition.

    :partition: The current partition to propose a flip from.
    :returns: a dictionary of with the flipped node mapped to its new assignment

    """
    edge = random.choice(tuple(partition['cut_edges']))
    index = random.choice((0, 1))

    flipped_node, other_node = edge[index], edge[1 - index]

    flip = {flipped_node: partition.assignment[other_node]}

    # self loop
    numEdges = 2.0 * len(partition['cut_edges'])
    if random.random() < 1.0 - (numEdges * 1.0 / partition.max_edge_cuts):
        flip = dict()
    return flip


def propose_several_random_flips(partition):
    number_of_flips = random.randint(2, 7)

    proposal = dict()

    for i in range(number_of_flips):
        proposal.update(propose_random_flip(partition))

    return proposal


def propose_flip_every_district(partition):
    proposal = dict()

    for dist_edges in partition['cut_edges_by_part'].values():
        edge = random.choice(list(dist_edges))

        index = random.choice((0, 1))
        flipped_node, other_node = edge[index], edge[1 - index]
        flip = {flipped_node: partition.assignment[other_node]}

        proposal.update(flip)

    return proposal


def propose_chunk_flip(partition):
    proposal = dict()

    edge = random.choice(tuple(partition['cut_edges']))
    index = random.choice((0, 1))

    flipped_node = edge[index]

    valid_flips = [nbr for nbr in partition.graph.neighbors(
        flipped_node) if partition.assignment[nbr] != partition.assignment[flipped_node]]

    for flipped_neighbor in valid_flips:
        proposal.update({flipped_neighbor: partition.assignment[flipped_node]})

    return proposal


def propose_flip_every_edge_of_district(partition):
    proposal = dict()

    edges = random.choice(list(partition['cut_edges_by_part'].values()))

    for edge in edges:
        if(random.random() > .5):
            index = random.choice((0, 1))
            flipped_node, other_node = edge[index], edge[1 - index]
            proposal.update({flipped_node: partition.assignment[other_node]})

    return proposal


def propose_single_or_chunk(partition):
    if(random.random() > .1):
        return propose_random_flip(partition)
    else:
        return propose_chunk_flip(partition)


def number_of_flips(partition, dict_of_flips, prev_partition):
    flips = partition.flips
    if flips is None or flips is prev_partition:
        return dict_of_flips, prev_partition
    else:
        prev_partition = flips
        dict_of_flips[next(iter(flips))] = dict_of_flips.get(next(iter(flips)), 0) + 1
        return dict_of_flips, prev_partition
