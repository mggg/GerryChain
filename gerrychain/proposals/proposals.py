from ..random import random


def propose_any_node_flip(partition):
    """Propose to pick a random node to a
    random part

    """

    node = random.choice(tuple(partition.assignment.keys()))
    newpart = random.choice(partition.parts)

    return {node: newpart}


def propose_flip_every_district(partition):
    """Proposes a random boundary flip for each district in the partition.

    :param partition: The current partition to propose a flip from.
    :return: a dictionary with the flipped nodes mapped to their new assignments

    """
    proposal = dict()

    for dist_edges in partition["cut_edges_by_part"].values():
        edge = random.choice(list(dist_edges))

        index = random.choice((0, 1))
        flipped_node, other_node = edge[index], edge[1 - index]
        flip = {flipped_node: partition.assignment[other_node]}

        proposal.update(flip)

    return proposal


def propose_chunk_flip(partition):
    """Chooses a random boundary node and proposes to flip it and all of its neighbors

    :param partition: The current partition to propose a flip from.
    :return: a dictionary with the flipped nodes mapped to their new assignments

    """
    proposal = dict()

    edge = random.choice(tuple(partition["cut_edges"]))
    index = random.choice((0, 1))

    flipped_node = edge[index]

    valid_flips = [
        nbr
        for nbr in partition.graph.neighbors(flipped_node)
        if partition.assignment[nbr] != partition.assignment[flipped_node]
    ]

    for flipped_neighbor in valid_flips:
        proposal.update({flipped_neighbor: partition.assignment[flipped_node]})

    return proposal


def propose_random_flip(partition):
    """Proposes a random boundary flip from the partition.

    :param partition: The current partition to propose a flip from.
    :return: a dictionary with the flipped node mapped to its new assignment

    """
    if len(partition["cut_edges"]) == 0:
        return dict()

    edge = random.choice(tuple(partition["cut_edges"]))
    index = random.choice((0, 1))

    flipped_node, other_node = edge[index], edge[1 - index]

    flip = {flipped_node: partition.assignment[other_node]}

    return flip


flip = propose_random_flip
