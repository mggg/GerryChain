"""
This module provides the main acceptance function used in ReCom Markov chains.

Dependencies:

- random: For random number generation for probabilistic acceptance.

Last Updated: 11 Jan 2024
"""

import random

from gerrychain.partition import Partition


def always_accept(partition: Partition) -> bool:
    return True


def cut_edge_accept(partition: Partition) -> bool:
    """
    Always accepts the flip if the number of cut_edges decreases.
    Otherwise, uses the Metropolis criterion to decide.

    :param partition: The current partition to accept a flip from.
    :type partition: Partition

    :returns: True if accepted, False to remain in place
    :rtype: bool
    """
    # frm: TODO: Documentation: Add documentation on what the "Metropolis criterion" is...
    #
    # The math is not important, what is important is what the goal is.
    # I tried to figure this out, but failed.  I assume that the answer is that
    # there is some statistical property of the Metropolis Criterion that is
    # useful, but at a higher level, it is not clear (to me) what cut_edge_accept()
    # is trying to do.

    bound = 1.0

    if partition.parent is not None:
        bound = min(1, len(partition.parent["cut_edges"]) / len(partition["cut_edges"]))

    return random.random() < bound
