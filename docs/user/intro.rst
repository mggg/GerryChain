.. _introduction:

Overview of the Chain
=====================

RunDMCMC is intended to help the analysis of districting plans via random walks
on Markov chains.


Parts of the chain
------------------

During any step in the chain's random walk, it relies on four layers to
function properly. These layers are the **proposal functions**, **updaters**,
**validators**, and **acceptance functions**. These states are handled by
user-provided functions, so the chain can be configured solely by choosing new
functions in these layers.
