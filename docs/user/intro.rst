.. _introduction:

Overview of the Chain
=====================

GerryChain is useful for detecting gerrymandered district plans.

It does this by determining whether a given district plan is an 
outlier with respect to the universe of all possible district plans
that adhere to a given set of rules.  Note that each state determines 
its own set of rules for creating district plans, but an example of 
such a rule is to prefer compact districts (ones that look more 
like a circle) over districts that look like salamanders (thin with 
long branches).

The universe of all possible district plans for a given state is huge, 
so the challenge is to create a subset of all possible plans that 
reasonably represents the universe of plans.  GerryChain does this by
randomly sampling the universe of all plans to create an "ensemble"
of plans.  One can then examine that ensemble to see if a specific 
district plan is an outlier relative to the ensemble.

GerryChain uses a Markov Chain approach that starts with an 
initial district plan and then randomly alters an adjacent pair of
districts to create a new plan. That new plan then has another
pair of adjacent districts selected to randomly alter and this creates
a third possible plan. Continuing in this way for thousands or millions
of steps then produces an ensemble of possible plans which may
be used for analyis.

Note that GerryChain represents a district plan as a partition of a graph with 
nodes that define a geographical area (such as a voting precinct or a census block)
and edges that encode the notion of adjacency or contiguity used in the analysis.
Often an edge represents two geographic units sharing a boundary, but
the graph may require additions or removals for point contacts, water
connections, islands, data errors, or jurisdiction-specific contiguity rules.

A district then is a collection of nodes, and a district plan is 
the overall assignment of nodes to districts.

Parts of the chain
------------------

GerryChain performs a random walk over all partitions of a graph.  It does this
with a simple Markov chain. The chain's behavior is entirely governed by four
modular layers: **proposals**, **updaters**, **validators**, and **acceptance
functions**. 

These layers are implemented as functions and as a result, the behavior of
the chain can be changed by changing the function used.  The GerryChain codebase
provides several options for the functions for each layer, as well as 
defaults.  However, a motivated user can define their own function and 
tell GerryChain to use that instead.

The layers function as follows:

.. glossary::

    Proposals
        A proposal is an algorithm for creating a new district map from 
        an existing one.  A simple example is to just pick one node (for
        instance a census block) and reassign it to a different district.
        Another example would be to merge two districts and then 
        randomly split the merged nodes into two new districts.
        
    Updaters
        An updater computes one or more metrics about a district plan
        for later layers to use. One example of an updater is to 
        compute the edges that form the boundary between two districts,
        that is, the edges where one node is in one district and the 
        other node is in a different district.  Another example would
        be computing the relative percentages of Democratic vs. 
        Republican votes (based on past election results) for each
        district in the district plan.

    Validators
        A validator decides whether or not a new district plan is valid for 
        the chain to move to. For instance, often the redistricting rules require 
        that congressional districts be contiguous. A validator may 
        require that all proposed steps create only
        contiguous districts.

    Acceptance functions
        An acceptance function decides whether or not the chain *should* 
        move to a new, valid state.  This is useful for implementing 
        techniques such as the Metropolis-Hastings_ algorithm.


.. _`Metropolis-Hastings`: https://en.wikipedia.org/wiki/Metropolis%E2%80%93Hastings_algorithm

Workflow for a new GerryChain Project
-------------------------------------

* **Get the data** 
    You will need data that defines distinct geographic areas (your nodes)
    and records the neighbors of each node (your edges).  You will also 
    need data about each of the nodes, for instance, population and 
    perhaps past voting data, or ethnic makeup, etc.

    Often you will need to combine data from multiple sources which 
    can be challenging.  

* **Clean the data**
    Unfortunately data often needs to be "cleaned" to be ready to use
    by GerryChain.  For example, the rules for many district plans 
    include a rule that districts must be contiguous, which leaves 
    open the issue of what to do with a physical island which is cut
    off from the mainland by water.  You may need to modify the 
    underlying data to artificially connect the island nodes 
    to nodes on the mainland.

* **Create a graph of the data**
    As you will see later, there are convenient functions to create
    a graph once you have clean data.

* **Pick a Proposal function**
    This is the way the Markov Chain will create a new district 
    plan from the current plan.  For instance, as we will see later, one
    might pick "ReCom" which merges two adjacent districts and then randomly
    splits them into two new districts.

* **Create an initial district plan**
    The choice of an initial plan is typically not super important, as
    whatever you select as your initial plan will end up as just one
    plan in the ensemble of perhaps thousands or hundreds of thousands
    of plans, but you do need a starting point.

* **Decide on what data to calculate for each Markov Chain step**
    To decide if a given district plan is an outlier, you need to 
    calculate the data that defines the metric you are evaluating.
    One fairly common metric is whether a district in a plan is a 
    safe Democratic district or a safe Republican district.  Given
    that metric for each district in each district plan, one can 
    determine if the number of safe districts in a given plan is
    an outlier.  

    The calculations you choose will become updater functions.

* **Kick off the Markov Chain**
    Tell the system how many district plans it should generate 
    and turn it loose.

* Post process the results of the Markov Chain run.
    This typically involves analysis of the data that your 
    updater functions computed to generate summary statistics 
    and/or charts.

This may seem daunting, but GerryChain has defaults for the most 
common choices and there are datasets available that are already
"clean" to use inside GerryChain.  You can customize almost 
anything in GerryChain, but you do not need to.
