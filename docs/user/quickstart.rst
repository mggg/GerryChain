.. _quickstart:

===============
Getting started
===============

This guide will show you how to start generating ensembles with GerryChain, using MGGG's own
`Massachusetts shapefile`_.

.. `Massachusetts shapefile`: https://github.com/mggg-states/MA-shapefiles/

What you'll need
================

Before we can start running Markov chains, you'll need to:

* Install ``gerrychain`` from PyPI by running ``pip install gerrychain`` in a terminal.
* Download and unzip MGGG's `shapefile of Massachusetts's 2002-2010 precincts`_ from GitHub.
* Open your favorite python environment (JupyterLab, ipython, or just a ``.py`` file in
    your favorite editor) in the directory containing the ``MA_precincts_02_10.shp`` file
    from the ``.zip`` that you downloaded and unzipped.

.. `shapefile of Massachusetts's 2002-2010 precincts`: https://github.com/mggg-states/MA-shapefiles/blob/master/MA_precincts_02_10.zip

.. TODO: conda instructions

Creating the initial partition
==============================

In order to run a Markov chain, we need an
adjacency :class:`~gerrychain.Graph` of our VTD geometries and
:class:`~gerrychain.Partition` of our adjacency graph into districts. This Partition
will be the initial state of our Markov chain.

.. code-block:: python

    from gerrychain import Graph, Partition
    from gerrychain.updaters import Tally

    graph = Graph.from_file("./MA_precincts_02_10.shp")

    graph.to_json("./MA_precincts_02_10_graph.json")

    initial_partition = Partition(
        graph,
        assignment="CD",
        updaters={
            "population": Tally("POP2000", alias="population")
        }
    )

Here's what's happening in this code block.

The :meth:`Graph.from_file() <gerrychain.Graph.from_file>` classmethod creates a
:class:`~gerrychain.Graph` of the precincts in our shapefile. By default, this method
copies all of the data columns from the shapefile's attribute table to the ``graph`` object
as node attributes. The contents of this particular shapefile's attribute table are
summarized in the `mggg-states/MA-shapefiles <https://github.com/mggg-states/MA-shapefiles#metadata>`_
GitHub repo.
    
Depending on the size of the state, the process of generating an adjacency graph can
take a long time. To avoid having to repeat this process in the future, we call 
:meth:`graph.to_json() <gerrychain.Graph.to_json>` to save the graph
in the NetworkX ``json_graph`` format under the name ``"MA_precincts_02_10_graph.json``.

Finally, we create a :class:`~gerrychain.Partition` of the graph.
This will be the starting point for our Markov chain. The :class:`~gerrychain.Partition` class
takes three arguments:

1. A ``graph``.
2. An ``assignment`` of the nodes of the graph into parts of the partition. This can be either
    a dictionary mapping node IDs to part IDs, or the string key of a node attribute that holds
    each node's assignment. In this example we've written ``assignment="CD"`` to tell the :class:`~gerrychain.Partition`
    to assign nodes by their ``"CD"`` attribute that we copied from the shapefile. This attributes holds the
    assignments of precincts to Congressional Districts from the 2000 Redistricting cycle.
3. An optional ``updaters`` dictionary. Here we've provided a single updater named ``"population"`` that
    computes the total population of each district in the partition, based on the ``"POP2000"`` node attribute
    from our shapefile.

With the ``"population"`` updater configured, we can see the total population in each of our Congressional Districts.

.. code-block:: python
    >>> print(initial_partition["population"])
    {


For more information on updaters, see :doc:`updaters` and the :mod:`gerrychain.updaters` documentation.

Running a chain
===============

Now that we have our initial partition, we can configure and run a :class:`Markov chain <gerrychain.MarkovChain>`.
Let's configure a short Markov chain to make sure everything works properly.

.. code-block:: python

    from gerrychain import MarkovChain
    from gerrychain.constraints import Validator, single_flip_contiguous
    from gerrychain.proposals import propose_random_flip
    from gerrychain.accept import always_accept

    chain = MarkovChain(
        proposal=propose_random_flip,
        is_valid=Validator([single_flip_contiguous]),
        accept=always_accept,
        initial_state=initial_partition,
        total_steps=1000
    )

Let's 

Computing election results
==========================