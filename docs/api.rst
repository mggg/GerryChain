.. _api_reference:


API Reference
=============

The public API is divided by the role each component plays in a GerryChain workflow.

Core structures
---------------

.. grid:: 1 2 3 3
    :gutter: 3

    .. grid-item-card:: Graphs
        :link: api/graphs
        :link-type: doc

        Geographic units and their adjacency relationships.

    .. grid-item-card:: Partitions
        :link: api/partitions
        :link-type: doc

        District assignments and plan statistics.

    .. grid-item-card:: Markov chains
        :link: api/chains
        :link-type: doc

        Chain configuration, iteration, and state transitions.

Building chains
---------------

.. grid:: 1 2 2 2
    :gutter: 3

    .. grid-item-card:: Proposals and constraints
        :link: api/proposals_constraints
        :link-type: doc

        Candidate plans and the rules used to validate them.

    .. grid-item-card:: Updaters and elections
        :link: api/updaters
        :link-type: doc

        Derived statistics, election results, and incremental updates.

Utilities and analysis
----------------------

.. grid:: 1 2 2 2
    :gutter: 3

    .. grid-item-card:: Grids and spanning trees
        :link: api/trees
        :link-type: doc

        Synthetic grids and tree-based partitioning tools.

    .. grid-item-card:: Metrics and diversity
        :link: api/metrics
        :link-type: doc

        Compactness, partisan statistics, and ensemble diversity.

.. toctree::
    :hidden:
    :maxdepth: 1

    api/graphs
    api/partitions
    api/chains
    api/proposals_constraints
    api/updaters
    api/trees
    api/metrics
