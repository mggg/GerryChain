"""Random number generator normalization for GerryChain."""

from __future__ import annotations

import numbers
import random


def make_rng(rng: random.Random | int | None = None) -> random.Random:
    """Return ``rng`` or create a ``Random`` from a seed or system entropy."""
    if isinstance(rng, random.Random):
        return rng
    if rng is None:
        return random.Random()
    if isinstance(rng, bool):
        raise TypeError("rng must be a random.Random instance, an integer seed, or None")
    if isinstance(rng, numbers.Integral):
        return random.Random(int(rng))
    raise TypeError("rng must be a random.Random instance, an integer seed, or None")
