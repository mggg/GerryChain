from __future__ import annotations

from .random import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gerrychain.grid import Grid
    from gerrychain.partition.partition import Partition
    from typing import Union


def always_accept(partition: Union[Grid, Partition]) -> bool:
    return True


def cut_edge_accept(partition: Union[Grid, Partition]) -> bool:
    """Always accepts the flip if the number of cut_edges increases.
    Otherwise, uses the Metropolis criterion to decide.

    :param partition: The current partition to accept a flip from.
    :return: True if accepted, False to remain in place

    """
    bound = 1

    if partition.parent is not None:
        bound = min(1, len(partition.parent["cut_edges"]) / len(partition["cut_edges"]))

    return random.random() < bound
