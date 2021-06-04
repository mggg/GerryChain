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

GerryChain is a Python library for building ensembles of districting plans
using `Markov chain Monte Carlo`_. It is developed and maintained by the
`Metric Geometry and Gerrymandering Group`_ and our network of volunteers.
It is distributed under the `3-Clause BSD License`_.

The basic workflow is to start with the geometry of an initial plan and
generate a large collection of sample plans for comparison. Usually, we
will constrain these sampled plans in such a way that they perform at
least as well as the initial plan according to traditional districting
principles, such as population balance or compactness. Comparing the
initial plan to the ensemble provides quantitative tools for measuring
whether or not it is an outlier among the sampled plans.

.. _`Voting Rights Data Institute`: http://gerrydata.org/
.. _chain: https://github.com/gerrymandr/cfp_mcmc
.. _`Markov chain Monte Carlo`: https://en.wikipedia.org/wiki/Markov_chain_Monte_Carlo
.. _`Metric Geometry and Gerrymandering Group`: https://www.mggg.org/
.. _`3-Clause BSD License`: https://opensource.org/licenses/BSD-3-Clause


Getting started
===============

See our `Getting started guide`_ for the basics of using GerryChain.

.. _`Getting started guide`: https://gerrychain.readthedocs.io/en/latest/user/quickstart.html

We also highly recommend the resources prepared by Daryl R. DeFord of MGGG
for the 2019 MIT IAP course `Computational Approaches for Political Redistricting`_.

.. _`Computational Approaches for Political Redistricting`: https://people.csail.mit.edu/ddeford//CAPR.php


Useful links
============

- `Documentation`_
- `Bug reports and feature requests`_
- `Contributions welcome!`_

.. _`Documentation`: https://gerrychain.readthedocs.io/en/latest/
.. _`Bug reports and feature requests`: https://github.com/mggg/gerrychain/issues
.. _`Contributions welcome!`: https://github.com/mggg/gerrychain/pulls


Installation
============

Using conda (recommended)
-------------------------

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

