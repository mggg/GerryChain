.. _quickstart:

===============================
Getting started with GerryChain
===============================

This guide will show you how to start generating ensembles with GerryChain, using MGGG's
`Pennsylvania shapefile`_.

.. _Pennsylvania shapefile: https://github.com/mggg-states/PA-shapefiles/

What you'll need
================

Before we can start running Markov chains, you'll need to:

* Install ``gerrychain`` from PyPI by running ``pip install gerrychain`` in a terminal.
* Download MGGG's `json of Pennsylvania's VTDs`_ from GitHub.
* Open your preferred Python environment (e.g. JupyterLab, IPython, or a ``.py`` file
  in your favorite editor) in the directory containing the ``PA_VTDs.json`` file
  that you downloaded.

.. _`json of Pennsylvania's VTDs`: https://github.com/mggg/GerryChain/blob/master/docs/user/PA_VTDs.json

.. TODO: conda instructions

Creating the initial partition
==============================

In order to run a Markov chain, we need an
adjacency :class:`~gerrychain.Graph` of our VTD geometries and
:class:`~gerrychain.Partition` of our adjacency graph into districts. This Partition
will be the initial state of our Markov chain. ::

    from gerrychain import Graph, Partition, Election
    from gerrychain.updaters import Tally, cut_edges

    graph = Graph.from_json("./PA_VTDs.json")

    election = Election("SEN12", {"Dem": "USS12D", "Rep": "USS12R"})

    initial_partition = Partition(
        graph,
        assignment="CD_2011",
        updaters={
            "cut_edges": cut_edges,
            "population": Tally("TOTPOP", alias="population"),
            "SEN12": election
        }
    )

Here's what's happening in this code block.

The :meth:`Graph.from_json() <gerrychain.Graph.from_json>` classmethod creates a
:class:`~gerrychain.Graph` of the precincts. By default, this method
copies all of the data columns from the shapefile's attribute table to the ``graph`` object
as node attributes. The contents of this particular shapefile's attribute table are
summarized in the `mggg-states/PA-shapefiles <https://github.com/mggg-states/PA-shapefiles#metadata>`_
GitHub repo.
    
Next, we configure an :class:`~gerrychain.Election` object representing the 2012 Senate election,
using the ``USS12D`` and ``USS12R`` vote total columns from our shapefile. The first argument
is a name for the election (``"SEN12"``), and the second argument is a dictionary matching political
parties to their vote total columns in our shapefile. This will let us compute
hypothetical election results for each districting plan in the ensemble.

Finally, we create a :class:`~gerrychain.Partition` of the graph.
This will be the starting point for our Markov chain. The :class:`~gerrychain.Partition` class
takes three arguments:

:graph: A graph.
:assignment: An assignment of the nodes of the graph into parts of the partition. This can be either
    a dictionary mapping node IDs to part IDs, or the string key of a node attribute that holds
    each node's assignment. In this example we've written ``assignment="CD_2011"`` to tell the :class:`~gerrychain.Partition`
    to assign nodes by their ``"CD_2011"`` attribute that we copied from the shapefile. This attributes holds the
    assignments of precincts to congressional districts from the 2010 redistricting cycle.
:updaters: An optional dictionary of "updater" functions. Here we've provided an updater named ``"population"`` that
    computes the total population of each district in the partition, based on the ``"TOTPOP"`` node attribute
    from our shapefile, and a "SEN12" updater that will output the election results for the ``election`` that we
    set up. We've also provided a ``cut_edges`` updater. This returns all of the edges in the graph
    that cross from one part to another, and is used by ``propose_random_flip`` to find a random boundary node to
    flip.

With the ``"population"`` updater configured, we can see the total population in each of our congressional districts.
In an interactive Python session, we can print out the populations like this::

    >>> for district, pop in initial_partition["population"].items():
    ...     print("District {}: {}".format(district, pop))
    District 3: 706653
    District 10: 706992
    District 9: 702500
    District 5: 695917
    District 15: 705549
    District 6: 705782
    District 11: 705115
    District 8: 705689
    District 4: 705669
    District 18: 705847
    District 12: 706232
    District 17: 699133
    District 7: 712463
    District 16: 699557
    District 14: 705526
    District 13: 705028
    District 2: 705689
    District 1: 705588

Notice that ``partition["population"]`` is a dictionary mapping the ID of each district to its total
population (that's why we can call the ``.items()`` method on it). Most updaters output values in this dictionary format.

For more information on updaters, see the :mod:`gerrychain.updaters` documentation.

Running a chain
===============

Now that we have our initial partition, we can configure and run a :class:`Markov chain <gerrychain.MarkovChain>`.
Let's configure a short Markov chain to make sure everything works properly. ::

    from gerrychain import MarkovChain
    from gerrychain.constraints import single_flip_contiguous
    from gerrychain.proposals import propose_random_flip
    from gerrychain.accept import always_accept

    chain = MarkovChain(
        proposal=propose_random_flip,
        constraints=[single_flip_contiguous],
        accept=always_accept,
        initial_state=initial_partition,
        total_steps=1000
    )

To configure a chain, we need to specify five objects.

:proposal: A function that takes the current state and returns new district assignments ("flips") for one
    or more nodes. This comes in the form of a dictionary mapping one or more node IDs to their new district IDs.
    Here we've used the ``propose_random_flip`` proposal, which proposes that a random node on the boundary of one
    district be flipped into the neighboring district.
:constraints: A list of binary constraints (functions that take a partition and return ``True`` or ``False``) that
    together define which districting plans. are valid. Here we've used just a single constraint, ``single_flip_contiguous``,
    which checks that each district in  the plan is contiguous. This particular constraint is
    optimized for the single-flip proposal function we are using (hence the name). We could add more
    constraints to require that districts have nearly-equal population, to impose a bound on the compactness of
    the districts according to some score, or to prevent districts from splitting more counties than the original plan.
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
this chain and print out the sorted vector of Democratic vote percentages in each district for each
step in the chain. ::

    for partition in chain:
        print(sorted(partition["SEN12"].percents("Dem")))

That's all: you've run a Markov chain!

To analyze the Republican vote percentages for each districting plan in our ensemble,
we'll want to actually collect the data, and not just print it out. We can use a list
comprehension to store these vote percentages, and then convert it into a :mod:`pandas`
:class:`~pandas.DataFrame`. ::

    import pandas

    d_percents = [sorted(partition["SEN12"].percents("Dem")) for partition in chain]

    data = pandas.DataFrame(d_percents)

This code will collect data from a different ensemble than our ``for`` loop above. Each time
we iterate through the ``chain`` object, we run a fresh new Markov chain (using the same
configuration that we defined when instantiating ``chain``).

The `pandas`_ :class:`DataFrame` object has many helpful methods for analyzing and plotting
data. For example, we can produce a boxplot of our ensemble's Democratic vote percentage
vectors, with the initial 2011 districting plan plotted in red, in just a few lines of code::

    import matplotlib.pyplot as plt
    
    ax = data.boxplot(positions=range(len(data.columns)))
    plt.plot(data.iloc[0], "ro")

    plt.show()

.. _`pandas`: https://pandas.pydata.org/

(Before you over-analyze this data, keep in mind that this is a toy ensemble of just
one thousand plans created by single flips.)

Next steps
==========

To see a more elaborate example that uses the ReCom proposal, see :doc:`./recom`.

To learn more about the specific components of GerryChain, see the :doc:`/api`.

.. proposals (recom), updaters, acceptance rules, scores
