.. _quickstart:

===============
Getting started
===============

This guide shows you how to start generating ensembles with GerryChain, **assuming that you already have 
a cleaned shapefile with all the necessary data**. This is an enormous assumption; collecting and cleaning
geospatial data is a challenging process with many possible points of failure.

Suppose we have a shapefile called ``vtds.shp`` containing the `2010 Tiger/Line Voting Tabulation District (VTD)`_
geometries of our favorite state or municipality, along with the following data columns:

- ``POP10``: Population counts for each VTD
- ``DISTRICT``: The district each VTD belongs to, in some districting plan
- ``D_VOTES``: The number of Democratic votes cast in each precinct, in some election
- ``R_VOTES``: The number of Republican votes cast in each precinct, in some election

In order to run a Markov chain on the districting plans for our state, we need an
adjacency :class:`~gerrychain.Graph` of our VTD geometries and a
:class:`~gerrychain.Partition` of our adjacency graph into districts. This Partition
will be the initial state of our Markov chain.

.. `2010 Tiger/Line Voting Tabulation District (VTD)`: https://www2.census.gov/geo/tiger/TIGER2010/VTD/2010/

Creating an adjacency graph
===========================

We construct the *adjacency graph* on our set of VTDs (the *nodes* of our graph)
by drawing an edge between any two VTDs that are adjacent.

.. note::
    
    An adjacency graph is different from the *dual graph* of the VTD geometries, which we would
    construct by drawing an edge between two VTDs *for each edge that they share*.
    An adjacency graph, by contrast, never has multiple edges between two nodes.

GerryChain provides a :class:`~gerrychain.graph.Graph` class that encapsulates this process::

    from gerrychain import Graph

    vtds_graph = Graph.from_file("./vtds.shp", adjacency="queen")

There are :class:`gerrychain.graph.Adjacency <two notions of adjacency>` that we can
use to construct our graphs. Many actual U.S. Congressional Districts are only Queen-contiguous,
so we use choose Queen contiguity in the above code example.

Depending on the size of the state, the process of generating an adjacency graph can take
a long time. To avoid having to repeat this process, we can save our graph as a JSON file::

    vtds_graph.to_json("./vtds_graph.json")

The next time we want to use our graph, we can just load it from the `vtds_graph.json` file::

    vtds_graph = Graph.from_json("./vtds_graph.json")

.. note:: 

    The GerryChain :class:`~gerrychain.Graph` is based on the :class:`~networkx.Graph`
    from the NetworkX library.
    We recommend reading the NetworkX documentation to learn how to work with it.

Partitioning the graph with an initial districting plan
=======================================================

Now that we have a graph, we can partition it into districts. Our shapefile has a data
column called ``"DISTRICT"`` assigning a district ID to each node in our adjacency graph.
We can use this assignment to instantiate a :class:`~gerrychain.Partition` object::

    from gerrychain import Partition

    initial_partition = Partition(vtds_graph, assignment="DISTRICT")

We set ``assignment="DISTRICT"`` to tell the :class:`~gerrychain.Partition` object to use
the ``"DISTRICT"`` node attribute to assign nodes into districts. The ``assignment``
parameter could also have been a dictionary from node ID to district ID. This is useful
when your adjacency graph and districting plan data are coming from two separate sources.

Running a chain
===============

Now that we have our initial partition, we can configure and run a
:class:`~gerrychain.MarkovChain <Markov Chain>`. Let's configure a Markov chain
of just a thousand steps, to make sure everything works properly:

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

For more information on the parameters we passed, see :module:`gerrychain.chain <the documentation>`.

Now we're ready to actually run the chain. The GerryChain :class:`~gerrychain.MarkovChain` is
an iterator that yields each state in the ensemble as it is created. This lets the user loop over
the chain and handle each state however they want---by printing to the console, making plots, recording
data, etc. For this example, let's print the perimeters of the districts in the districting plan,
for each plan in the ensemble::

    for partition in chain:
        print(partition["perimeter"])

This example also shows how you can access the data you've attached to the partition. Since our partition
is a :class:`~gerrychain.GeographicPartition`, it comes pre-configured with ``area`` and ``perimeter``
attributes that are re-calculated at each step in the chain. We access the value of the ``perimeter`` attribute
the same way we would access an item in a dictionary: ``partition["perimeter"]``. From the printed output,
we see that the value of the ``perimeter`` attribute is itself a dictionary mapping each district's ID to
the perimeter of the district.

Under the hood, these attributes are computed by "updater" functions. The user can pass their own
``updaters``dictionary when instantiating a ``Partition``, and the values will be accessible just like
the ``perimeter`` attribute above. For more details, see :module:`gerrychain.updaters`.

.. TODO: Elections