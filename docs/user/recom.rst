==========================
Running a chain with ReCom
==========================

This document shows how to run a chain using the ReCom proposal used in MGGG's
`2018 Virginia House of Delegates`_ report.

Our goal is to use ReCom to generate an ensemble of districting plans for Pennsylvania,
and then make a box plot comparing the Democratic vote shares for plans in our ensemble
to the 2011 districting plan that the Pennsylvania Supreme Court found to be a
Republican-favoring partisan gerrymander.

This code is also available as a Jupyter notebook `here`_.

.. _`2018 Virginia House of Delegates`: https://mggg.org/VA-report.pdf
.. _`here`: https://nbviewer.jupyter.org/github/mggg/gerrychain/tree/master/docs/notebooks/ReCom.ipynb

Imports
=======

The first step is to import everything we'll need::

    import matplotlib.pyplot as plt
    from gerrychain import (GeographicPartition, Partition, Graph, MarkovChain,
                            proposals, updaters, constraints, accept, Election)
    from gerrychain.tree_proposals import recom
    from functools import partial
    import pandas


Setting up the initial districting plan
=======================================

Now we can load the adjacency graph of our state's VTDs. We created this graph 
from MGGG's `Pennsylvania shapefile`_ and saved it as a ``.json`` in :ref:`quickstart`. ::

    graph = Graph.from_json("./PA_VTD.json")

We configure :class:`~gerrychain.Election` objects representing some of the election
data from our shapefile. ::

    elections = [
        Election("SEN10", {"Democratic": "SEN10D", "Republican": "SEN10R"}),
        Election("SEN12", {"Democratic": "USS12D", "Republican": "USS12R"}),
        Election("SEN16", {"Democratic": "T16SEND", "Republican": "T16SENR"}),
        Election("PRES12", {"Democratic": "PRES12D", "Republican": "PRES12R"}),
        Election("PRES16", {"Democratic": "T16PRESD", "Republican": "T16PRESR"})
    ]
    

.. _Pennsylvania shapefile: https://github.com/mggg-states/PA-shapefiles/

Configuring our updaters
------------------------

We want to set up updaters for everything we want to compute for each plan in the ensemble. ::
    
    # Population updater, for computing how close to equality the district
    # populations are. "TOT_POP" is the population column from our shapefile.
    my_updaters = {"population": updaters.Tally("TOT_POP", alias="population")}
    
    # Election updaters, for computing election results using the vote totals
    # from our shapefile.
    election_updaters = {election.name: election for election in elections}
    my_updaters.update(election_updaters)


Instantiating the partition
---------------------------

We can now instantiate the initial state of our Markov chain, using the 2011 districting plan::

    initial_partition = GeographicPartition(graph, assignment="2011_PLA_1", updaters=my_updaters)
    
:class:`~gerrychain.GeographicPartition` comes with built-in ``area`` and ``perimeter`` updaters.
We do not use them here, but they would allow us to compute compactness scores like Polsby-Popper
that depend on these measurements.

Setting up the Markov chain
===========================

Proposal
--------

First we'll set up the ReCom proposal. We need to fix some parameters using `functools.partial`
before we can use it as our proposal function. ::

    # The ReCom proposal needs to know the ideal population for the districts so that
    # we can improve speed by bailing early on unbalanced partitions.
    
    ideal_population = sum(initial_partition["population"].values()) / len(initial_partition)
    
    # We use functools.partial to bind the extra parameters (pop_col, pop_target, epsilon, node_repeats)
    # of the recom proposal.
    proposal = partial(recom,
                       pop_col="TOT_POP",
                       pop_target=ideal_population,
                       epsilon=0.02,
                       node_repeats=2
                      )


Constraints
-----------

To keep districts about as compact as the original plan, we bound the number
of cut edges at 2 times the number of cut edges in the initial plan. ::
    
    compactness_bound = constraints.UpperBound(
        lambda p: len(p["cut_edges"]),
        2*len(initial_partition["cut_edges"])
    )

    pop_constraint = constraints.within_percent_of_ideal_population(initial_partition, 0.02)
    

Configuring the Markov chain
----------------------------

.. code:: python

    chain = MarkovChain(
        proposal=proposal,
        constraints=[
            pop_constraint,
            compactness_bound
        ],
        accept=accept.always_accept,
        initial_state=initial_partition,
        total_steps=1000
    )

Running the chain
=================

Now we'll run the chain, putting the sorted Democratic vote percentages directly
into a :mod:`pandas` :class:`~pandas.DataFrame` for analysis and plotting. The ``DataFrame``
will have a row for each state of the chain. The first column of the ``DataFrame`` will
hold the lowest Democratic vote share among the districts in each partition in the chain, the
second column will hold the second-lowest Democratic vote shares, and so on. ::

    # This will take about 10 minutes.
    
    data = pandas.DataFrame(
        sorted(partition["SEN12"].percents("Democratic"))
        for partition in chain
    )
    
If you install the ``tqdm`` package, you can see a progress bar
as the chain runs by running this code instead::
    
    data = pandas.DataFrame(
        sorted(partition["SEN12"].percents("Democratic"))
        for partition in chain.with_progress_bar()
    )

Create a plot
=============

Now we'll create a box plot similar to those appearing the Virginia report. ::

    fig, ax = plt.subplots(figsize=(8, 6))

    # Draw 50% line
    ax.axhline(0.5, color="#cccccc")

    # Draw boxplot
    data.boxplot(ax=ax, positions=range(len(data.columns)))

    # Draw initial plan's Democratic vote %s (.iloc[0] gives the first row)
    data.iloc[0].plot(style="ro", ax=ax)

    # Annotate
    ax.set_title("Comparing the 2011 plan to an ensemble")
    ax.set_ylabel("Democratic vote % (Senate 2012)")
    ax.set_xlabel("Sorted districts")
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1])

    plt.show()


.. image:: recom_plot.svg

There you go! To build on this, here are some possible next steps:

* Add, remove, or tweak the constraints
* Use a different proposal from GerryChain, or create your own
* Perform a similar analysis on a different districting plan for Pennsylvania
* Perform a similar analysis on a different state
* Compute partisan symmetry scores like Efficiency Gap or Mean-Median, and
  create a histogram of the scores of the ensemble.
* Perform the same analysis using a different election than the 2012 Senate election
* Collect Democratic vote percentages for *all* the elections we set up, instead
  of just the 2012 Senate election.