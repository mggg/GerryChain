.. RunDMCMC documentation master file, created by
   sphinx-quickstart on Mon Jun 11 14:55:33 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

RunDMCMC
========

RunDMCMC is a project to randomly sample congressional district plans using
`Markov Chain Monte Carlo`_ methods. It was created by the `Metric Geometry and
Gerrymandering Group`_ (MG3) in their `Voting Rights Data Institute`_ (VRDI)
program. The project is hosted in the `Gerrymandr/RunDMCMC`_ GitHub repo.

.. _`Markov Chain Monte Carlo`: https://en.wikipedia.org/wiki/Markov_chain_Monte_Carlo
.. _`Metric Geometry and Gerrymandering Group`: http://sites.tufts.edu/gerrymandr/
.. _`Voting Rights Data Institute`: http://gerrydata.org/
.. _`Gerrymandr/RunDMCMC`: https://github.com/gerrymandr/RunDMCMC

User Guide
----------

These documents give a brief introduction and help a user get started. The
later parts describe how to customize parts of the chain.

.. toctree::
    :maxdepth: 1

    user/intro
    user/install
    user/quickstart
    user/examples

Developers' Guide
-----------------

These documents provide detailed references for classes and functions in
RunDMCMC.

.. toctree::
    :maxdepth: 2

    dev/layer_api
    api
