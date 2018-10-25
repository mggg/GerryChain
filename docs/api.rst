API Reference
===================

.. module:: gerrychain

This part of the documentation details the interface that developers will use
with the chain. For a high-level overview of the code's structure, see
:ref:`the overview <overview>`. For a user-friendly introduction, see :ref:`the
introduction <introduction>`.

.. contents:: Table of Contents
    :local:

Adjacency Graphs
----------------


.. autoclass:: gerrychain.Graph

.. autoclass:: gerrychain.graph.Adjacency
    :members: Rook Queen

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