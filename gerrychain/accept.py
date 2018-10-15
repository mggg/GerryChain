import random


def mpaccept(partition):
    # if partition.parent is None:
            # return True
    val = 1
    # if (partition["POPB%"][3] > .5) and (partition["POPB%"][4] > .5):
    # return True
    if (partition["POPB%"][1] < .44) and partition["POPB%"][1] < partition.parent["POPB%"][1]:
        val = 0
    if (partition["POPB%"][3] < .44) and partition["POPB%"][3] < partition.parent["POPB%"][3]:
        val = 0
    if (partition["POPB%"][4] < .44) and partition["POPB%"][4] < partition.parent["POPB%"][4]:
        val = 0
    return (val + .05) > random.random()


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
    # Doesn't work currently
    bound = 1

    if partition.parent is not None:
        bound = min(1,
                    len(partition.parent["metagraph_degree"]) / len(partition["metagraph_degree"]))

    return random.random() < bound
