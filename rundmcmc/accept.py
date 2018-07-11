import random

def always_accept(partition):
    return True


def cut_edge_accept(partition):
    """Always accepts the flip if the number of cut_edges increases.
    Otherwise, uses the Metropolis criterion to decide.

    :partition: The current partition to accept a flip from.
    :returns: True if accepted, False to remain in place

    """
    bound = 1
    
    if partition.parent is not None:
        bound = min(1, len(partition.parent["cut_edges"]) / len(partition["cut_edges"]))

    return random.random() < bound


def metagraph_accept(partition):
    """Always accepts the flip if the metagraph degree increases.
    Otherwise, uses the Metropolis criterion to decide.

    :partition: The current partition to accept a flip from.
    :returns: True if accepted, False to remain in place

    """
    bound = 1
    
    if partition.parent is not None:
        bound = min(1,len(partition.parent["metagraph_degree"]) / len(partition["metagraph_degree"]))

    return random.random() < bound
