===============================
GerryChain
===============================


.. image:: https://readthedocs.org/projects/gerrychain/badge/?version=latest
   :target: https://gerrychain.readthedocs.io/en/latest
   :alt: Documentation Status


This code implements exploration of districting plans, exploring
the space around an initial districting plan to give some idea of the degree of
gerrymandering.

The development of this package began at the `Voting Rights Data Institute`_
as a Python rewrite of the chain_ C++ program, originally by Maria Chikina, Alan
Frieze and Wesley Pegden, for their paper, `"Assessing significance in a Markov
chain without mixing"`_.

- **Website (with documentation):** https://gerrychain.readthedocs.io/en/latest/
- **Bug reports:** https://github.com/mggg/gerrychain/issues


.. _`Voting Rights Data Institute` http://gerrydata.org/
.. _chain https://github.com/gerrymandr/cfp_mcmc
.. _`"Assessing significance in a Markov chain without mixing"` http://www.pnas.org/content/114/11/2860)

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