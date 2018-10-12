===============================
GerryChain
===============================


.. image:: https://readthedocs.org/projects/gerrychain/badge/?version=latest
   :target: https://gerrychain.readthedocs.io/en/latest
   :alt: Documentation Status

GerryChain is a Python library for building ensembles of districting plans
using `Markov chain Monte Carlo`_.

The basic workflow is to start with the geometry of an initial plan, perhaps one
that is currently enacted in your state or municipality, and generate a large
collection of sample plans for comparison. Usually, we will constrain these
sampled plans in such a way that they perform at least as well as the initial
plan according to traditional districting principles, such as population balance
or compactness. Comparing the initial plan to the ensemble provides quantitative
tools for measuring whether or not it is an outlier similar plans.

The development of this package began at the `Voting Rights Data Institute`_
as a Python rewrite of the chain_ C++ program, originally by Maria Chikina, Alan
Frieze and Wesley Pegden, for their paper `"Assessing significance in a Markov chain without mixing"`_.

.. _`Voting Rights Data Institute`: http://gerrydata.org/
.. _chain: https://github.com/gerrymandr/cfp_mcmc
.. _`"Assessing significance in a Markov chain without mixing"`: http://www.pnas.org/content/114/11/2860
.. _`Markov chain Monte Carlo`: https://en.wikipedia.org/wiki/Markov_chain_Monte_Carlo


Useful links
============

- `Documentation`_ <https://gerrychain.readthedocs.io/en/latest/>`_
- `Bug reports and feature requests`_ <https://github.com/mggg/gerrychain/issues>`_
- `Contributions welcome!`_

.. _`Documentation`: https://gerrychain.readthedocs.io/en/latest/
.. _`Bug reports and feature requests`: https://github.com/mggg/gerrychain/issues
.. _`Contributions welcome!`: https://github.com/mggg/gerrychain/pulls


Example
=======

.. code-block:: python
    from gerrychain import Graph, MarkovChain, GeographicPartition, Election
    from gerrychain.proposals import propose_random_flip
    from gerrychain.accept import always_accept
    from gerrychain.constraints import single_flip_contiguous    
    from gerrychain.updaters.compactness import polsby_poppers

    pennsylvania = GeographicPartition.from_json_graph("./21/rook.json", assignment="CD113")
    
    chain = MarkovChain(
        proposal=propose_random_flip,
        is_valid=single_flip_contiguous,
        accept=always_accept,
        initial_state=pennsylvania,
        total_steps=1000
    )

    for districting_plan in chain:
        print(polsby_popper(districting_plan))


Installation
============

To install GerryChain, we currently recommend cloning the repository and
installing a development version manually::

    git clone https://github.com/mggg/gerrychain.git
    cd gerrychain
    python3 setup.py develop