.. GerryChain documentation master file, created by
   sphinx-quickstart on Mon Jun 11 14:55:33 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==========
GerryChain
==========

.. image:: https://circleci.com/gh/mggg/GerryChain.svg?style=svg
    :target: https://circleci.com/gh/mggg/GerryChain
    :alt: Build Status
.. image:: https://codecov.io/gh/mggg/GerryChain/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/mggg/GerryChain
    :alt: Code Coverage
.. image:: https://readthedocs.org/projects/gerrychain/badge/?version=latest
    :target: https://gerrychain.readthedocs.io/en/latest
    :alt: Documentation Status
.. image:: https://badge.fury.io/py/gerrychain.svg
    :target: https://pypi.org/project/gerrychain/
    :alt: PyPI Package
.. image:: https://img.shields.io/conda/vn/conda-forge/gerrychain.svg?color=%230099cd
    :target: https://anaconda.org/conda-forge/gerrychain
    :alt: conda-forge Package

GerryChain is a library for using `Markov Chain Monte Carlo`_ methods
to study the problem of political redistricting. Development of the
library began during the `2018 Voting Rights Data Institute`_ (VRDI).

The project is in active development in the `mggg/GerryChain`_ GitHub
repository, where `bug reports and feature requests`_, as well as 
`contributions`_, are welcome.


.. _`Markov Chain Monte Carlo`: https://en.wikipedia.org/wiki/Markov_chain_Monte_Carlo
.. _`Metric Geometry and Gerrymandering Group`: https://www.mggg.org/
.. _`2018 Voting Rights Data Institute`: http://gerrydata.org/
.. _`MGGG/GerryChain`: https://github.com/mggg/GerryChain
.. _`bug reports and feature requests`: https://github.com/mggg/gerrychain/issues
.. _`contributions`: https://github.com/mggg/gerrychain/pulls


.. include:: user/install.rst

.. toctree::
    :caption: User Guide
    :maxdepth: 2

    user/install
    user/quickstart
    user/recom
    user/partitions
    user/updaters
    user/islands
    user/real-life-plans

We also highly recommend the resources prepared by Daryl R. DeFord of
MGGG for the 2019 MIT IAP course `Computational Approaches for Political Redistricting`_.


.. _`Computational Approaches for Political Redistricting`: https://people.csail.mit.edu/ddeford//CAPR.php


.. toctree::
    :caption: API Reference
    :maxdepth: 2

    api


.. toctree::
    :caption: Topics
    :glob:

    topics/*
