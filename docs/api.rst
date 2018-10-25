API Reference
===================

.. module:: gerrychain

.. contents:: Table of Contents
    :local:

Adjacency Graphs
----------------

.. autoclass:: gerrychain.Graph

.. autoclass:: gerrychain.graph.Adjacency

Partitions
----------

.. automodule:: gerrychain.partition
    :members:
    :show-inheritance:

Markov Chains
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

To make it easier to play around with GerryChain, we have provided a :class:`~gerrychain.defaults.Grid`
class representing a partition of a grid graph. This is especially useful if you want to start experimenting
but do not yet have a clean set of data and geometries to build your graph from.

.. autoclass:: gerrychain.defaults.Grid