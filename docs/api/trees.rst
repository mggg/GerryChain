Grids and Spanning Trees
========================

Grids
-----

The :class:`~gerrychain.grid.Grid` class provides a partition of a grid graph for experiments
that do not require external geographic data.

.. autoclass:: gerrychain.grid.Grid

Spanning tree methods
---------------------

The :func:`~gerrychain.proposals.recom` proposal operates on `spanning trees`_ to generate new
contiguous districting plans with balanced population.

The :mod:`gerrychain.tree` module exposes functions for partitioning graphs with spanning trees.
These can implement proposal functions or generate initial plans, as described in MGGG's
`2018 Virginia House of Delegates`_ report.

.. _`2018 Virginia House of Delegates`: https://mggg.org/VA-report.pdf
.. _`spanning trees`: https://en.wikipedia.org/wiki/Spanning_tree

.. automodule:: gerrychain.tree
    :members:
