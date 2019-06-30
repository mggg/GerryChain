API Reference
===================

.. module:: gerrychain

.. contents:: Table of Contents
    :local:

Adjacency graphs
----------------

.. autoclass:: gerrychain.Graph

Partitions
----------

.. automodule:: gerrychain.partition
    :members:
    :show-inheritance:

Markov chains
-------------------------

.. autoclass:: gerrychain.MarkovChain
    :members:

Proposals
---------

.. automodule:: gerrychain.proposals
    :members:

Binary constraints
------------------

.. automodule:: gerrychain.constraints
    :members:

.. autoclass:: gerrychain.constraints.Validator

.. autoclass:: gerrychain.constraints.UpperBound

.. autoclass:: gerrychain.constraints.LowerBound

.. autoclass:: gerrychain.constraints.SelfConfiguringLowerBound

.. autoclass:: gerrychain.constraints.SelfConfiguringUpperBound

.. autoclass:: gerrychain.constraints.WithinPercentRangeOfBounds

Updaters
--------

.. automodule:: gerrychain.updaters
    :members:

Elections
---------

.. automodule:: gerrychain.updaters.election
    :members:

Grids
-----

To make it easier to play around with GerryChain, we have provided a :class:`~gerrychain.grid.Grid`
class representing a partition of a grid graph. This is especially useful if you want to start experimenting
but do not yet have a clean set of data and geometries to build your graph from.

.. autoclass:: gerrychain.grid.Grid

Spanning tree methods
---------------------

The :func:`~gerrychain.proposals.recom` proposal function operates on `spanning trees`_ of the
adjacency graph in order to generate new contiguous districting plans with balanced population.

The :mod:`gerrychain.tree` submodule exposes some helpful functions for partitioning graphs
using spanning trees methods. These may be used to implement proposal functions or to generate
initial plans for running Markov chains, as described in MGGG's `2018 Virginia House of Delegates`_
report.

.. _`2018 Virginia House of Delegates`: https://mggg.org/VA-report.pdf
.. _`spanning trees`: https://en.wikipedia.org/wiki/Spanning_tree

.. automodule:: gerrychain.tree
    :members:


Metrics
-------

.. automodule:: gerrychain.metrics
    :members:
