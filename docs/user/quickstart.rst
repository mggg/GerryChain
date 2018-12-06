.. _quickstart:

===============
Getting started
===============

This guide will show you how to start generating ensembles with GerryChain, using MGGG's own
`Massachusetts shapefile`_.

.. _Massachusetts shapefile: https://github.com/mggg-states/MA-shapefiles/

What you'll need
================

Before we can start running Markov chains, you'll need to:

* Install ``gerrychain`` from PyPI by running ``pip install gerrychain`` in a terminal.
* Download and unzip MGGG's `shapefile of Massachusetts's 2002-2010 precincts`_ from GitHub.
* Open your favorite Python environment (JupyterLab, IPython, or just a ``.py`` file in
    your favorite editor) in the directory containing the ``MA_precincts_02_10.shp`` file
    from the ``.zip`` that you downloaded and unzipped.

.. _`shapefile of Massachusetts's 2002-2010 precincts`: https://github.com/mggg-states/MA-shapefiles/blob/master/MA_precincts_02_10.zip

.. TODO: conda instructions

Creating the initial partition
==============================

In order to run a Markov chain, we need an
adjacency :class:`~gerrychain.Graph` of our VTD geometries and
:class:`~gerrychain.Partition` of our adjacency graph into districts. This Partition
will be the initial state of our Markov chain.

.. code-block:: python

    from gerrychain import Graph, Partition
    from gerrychain.updaters import Tally, cut_edges

    graph = Graph.from_file("./MA_precincts_02_10.shp")

    graph.to_json("./MA_precincts_02_10_graph.json")

    initial_partition = Partition(
        graph,
        assignment="CD",
        updaters={
            "cut_edges": cut_edges,
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

:graph: A graph.
:assignment: An assignment of the nodes of the graph into parts of the partition. This can be either
    a dictionary mapping node IDs to part IDs, or the string key of a node attribute that holds
    each node's assignment. In this example we've written ``assignment="CD"`` to tell the :class:`~gerrychain.Partition`
    to assign nodes by their ``"CD"`` attribute that we copied from the shapefile. This attributes holds the
    assignments of precincts to Congressional Districts from the 2000 Redistricting cycle.
:updaters: An optional dictionary of "updater" functions. Here we've provided an updater named ``"population"`` that
    computes the total population of each district in the partition, based on the ``"POP2000"`` node attribute
    from our shapefile. We've also provided a ``cut_edges`` updater. This returns all of the edges in the graph
    that cross from one part to another, and is used by ``propose_random_flip`` to find a random boundary flip.

With the ``"population"`` updater configured, we can see the total population in each of our Congressional Districts.
In an interactive Python session, we can print out the populations like this:

.. code-block:: python
    >>> for district, pop in initial_partition["population"].items():
    ...     print("District {}: {}".format(district, pop))
    District 02: 686362
    District 01: 719068
    District 04: 706137
    District 05: 709963
    District 08: 702683
    District 07: 701696
    District 09: 712662
    District 03: 698459
    District 06: 711373

From this example, note that ``partition["population"]`` is a dictionary mapping the ID of each district to its total
population (that's why we can call the ``.items()`` method on it). Most updaters output values in this dictionary format.

For more information on updaters, see :doc:`updaters` and the :mod:`gerrychain.updaters` documentation.

Running a chain
===============

Now that we have our initial partition, we can configure and run a :class:`Markov chain <gerrychain.MarkovChain>`.
Let's configure a short Markov chain to make sure everything works properly.

.. code-block:: python

    from gerrychain import MarkovChain
    from gerrychain.constraints import single_flip_contiguous
    from gerrychain.proposals import propose_random_flip
    from gerrychain.accept import always_accept

    chain = MarkovChain(
        proposal=propose_random_flip,
        is_valid=single_flip_contiguous),
        accept=always_accept,
        initial_state=initial_partition,
        total_steps=1000
    )

To configure a chain, we need to specify five objects.

:proposal: A function that takes the current state and returns new district assignments ("flips") for one
    or more nodes. This comes in the form of a dictionary mapping one or more node IDs to their new district IDs.
    Here we've used the ``propose_random_flip`` proposal, which proposes that a random node on the boundary of one
    district be flipped into the neighboring district.
:is_valid: A function that takes a proposed state and returns ``True`` or ``False`` depending on whether
    the state satisfies all the constraints that we want to impose. Here we've used just a single constraint,
    called ``single_flip_contiguous``, which checks that each district is contiguous. This particular constraint is
    optimized for the single-flip proposal function we are using (hence the name).
:accept: A function that takes a valid proposed state and returns ``True`` or ``False`` to signal whether
    the random walk should indeed move to the proposed state. ``always_accept`` always accepts valid proposed states.
    If you want to implement Metropolis-Hastings or any other more sophisticated acceptance criterion, you can
    specify your own custom acceptance function here.
:initial_state: The first state of the random walk.
:total_steps: The total number of steps to take. Invalid proposals are not counted toward this total, but
    rejected (by ``accept``) valid states are.

For more information on the details of our Markov chain implementation, consult
the :class:`gerrychain.MarkovChain` documentation and source code.

The above code configures a Markov chain called ``chain``, but does *not* run it yet. We run the chain
by iterating through all of the states using a ``for`` loop. As an example, let's iterate through
this chain and print out the district populations, sorted, for each step in the chain.

.. code-block:: python

    for partition in chain:
        print(sorted(partition["population"].values()))

That's all: you've run a Markov chain!

Next steps
==========

* Updaters
* Proposals
* Constraints
* Acceptance rules
* Computing election results