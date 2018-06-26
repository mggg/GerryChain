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
