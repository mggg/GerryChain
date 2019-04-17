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


Installation
============

Using conda (recommended)
-----------------------------

To install GerryChain from conda-forge_ using conda_, run

.. code-block:: console

    conda install -c conda-forge gerrychain

For this command to work as intended, you will first need to activate
the conda environment that you want to install GerryChain in. If
the environment you want to activate is called ``vrdi`` (for example),
then you can do this by running

.. code-block:: console

    conda activate vrdi

If this command causes problems, make sure conda is up-to-date by
running

.. code-block:: console

    conda update conda
    conda init

For more information on using conda to install packages and manage
dependencies, see `Getting started with conda`_.

.. _`Getting started with conda`: https://conda.io/projects/conda/en/latest/user-guide/getting-started.html
.. _conda: https://conda.io/projects/conda/en/latest/
.. _conda-forge: https://conda-forge.org/

Using ``pip``
-------------

To install GerryChain from PyPI_, run ``pip install gerrychain`` from
the command line.

This approach often fails due to compatibility issues between our
different Python GIS dependencies, like ``geopandas``, ``pyproj``,
``fiona``, and ``shapely``. For this reason, we recommend installing
from conda-forge for most users.

.. _PyPI: https://pypi.org/


User Guide
==========

These guides show you how to get started using GerryChain:

.. toctree::
    :maxdepth: 2

    user/quickstart
    user/recom

We also highly recommend the resources prepared by Daryl R. DeFord of
MGGG for the 2019 MIT IAP course `Computational Approaches for Political Redistricting`_.


.. _`Computational Approaches for Political Redistricting`: https://people.csail.mit.edu/ddeford//CAPR.php

API Reference
=============

This document provides detailed documentation for classes and functions in
GerryChain.

.. toctree::
    :maxdepth: 2

    api


Topics
======

.. toctree::
    :glob:

    topics/*
