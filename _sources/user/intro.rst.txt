.. _introduction:

Overview of the Chain
=====================

GerryChain helps in analyzing districting plans via random walks. This is done
via a simple, but extendable, Markov chain. This is a brief, non-technical
overview of the chain.

The intended purpose of GerryChain is to analyze districting plans for
gerrymandering. Given an initial districting plan, making small, random changes
to the plan gives some sense of what the initial plan looks like *in context*.
The hope is that partisan gerrymandering can be detected by observing that
certain plans are extreme outliers in context with related plans.


Parts of the chain
------------------

GerryChain performs a random walk over all partitions of a graph.  It does this
with a simple Markov chain. The chain's behavior is entirely directed by four
modular layers: **proposals**, **updaters**, **validators**, and **acceptance
functions**. These layers are merely functions provided by the user, so the
chain can be configured by choosing or writing new functions for each step.

The layers function as follows:

.. glossary::

    Proposals
        Choose a new state for the Markov chain. For instance, given a
        congressional map, move one census block from one district to another.

    Updaters
        Compute various metrics about a state for later layers to use. For
        instance, the edges on the graph that go between one district to
        another.

    Validators
        Decide whether or not a state is valid for the chain to move to. For
        instance, many states require that congressional districts be
        contiguous. A validator may require that all proposed steps create only
        contiguous districts.

    Acceptance functions
        Decide whether or not the chain *should* move to a new, valid state.
        This is useful for implementing techniques such as the
        Metropolis-Hastings_ algorithm.


.. _`Metropolis-Hastings`: https://en.wikipedia.org/wiki/Metropolis%E2%80%93Hastings_algorithm
