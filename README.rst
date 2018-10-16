===============================
GerryChain
===============================

.. image:: https://circleci.com/gh/mggg/GerryChain.svg?style=svg
    :target: https://circleci.com/gh/mggg/GerryChain
    :alt: Build Status
.. image:: https://codecov.io/gh/mggg/GerryChain/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/mggg/GerryChain
   :alt: Code Coverage
.. image:: https://readthedocs.org/projects/gerrychain/badge/?version=latest
   :target: https://gerrychain.readthedocs.io/en/latest
   :alt: Documentation Status

GerryChain is a Python library for building ensembles of districting plans
using `Markov chain Monte Carlo`_. It is developed and maintained by the `Metric
Geometry and Gerrymandering Group`_ and our network of volunteers.

The basic workflow is to start with the geometry of an initial plan and generate a large
collection of sample plans for comparison. Usually, we will constrain these
sampled plans in such a way that they perform at least as well as the initial
plan according to traditional districting principles, such as population balance
or compactness. Comparing the initial plan to the ensemble provides quantitative
tools for measuring whether or not it is an outlier among the sampled plans.

.. _`Voting Rights Data Institute`: http://gerrydata.org/
.. _chain: https://github.com/gerrymandr/cfp_mcmc
.. _`"Assessing significance in a Markov chain without mixing."`: http://www.pnas.org/content/114/11/2860
.. _`Markov chain Monte Carlo`: https://en.wikipedia.org/wiki/Markov_chain_Monte_Carlo
.. _`Metric Geometry and Gerrymandering Group`: https://www.mggg.org/


Getting started
===============

See our `Getting started guide`_ for the basics of using GerryChain.

.. _`Getting started guide`: https://gerrychain.readthedocs.io/en/latest/user/quickstart.html


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

To install GerryChain from PyPI_, just run ``pip install gerrychain``.

.. _PyPI: https://pypi.org/
