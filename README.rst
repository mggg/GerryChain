===============================
GerryChain
===============================


.. image:: https://circleci.com/gh/gerrymandr/RunDMCMC.svg?style=svg
    :target: https://circleci.com/gh/gerrymandr/RunDMCMC
.. image:: https://codecov.io/gh/gerrymandr/RunDMCMC/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/gerrymandr/RunDMCMC
.. image:: https://api.codacy.com/project/badge/Grade/b02dfe3d778b40f3890d228889feee52
   :target: https://www.codacy.com/app/msarahan/RunDMCMC?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=gerrymandr/RunDMCMC&amp;utm_campaign=Badge_Grade
.. image:: https://readthedocs.org/projects/rundmcmc/badge/?version=latest
   :target: https://rundmcmc.readthedocs.io/en/latest
   :alt: Documentation Status


This code implements exploration of districting plans, exploring
the space around an initial districting plan to give some idea of the degree of
gerrymandering.

This package began as a Python rewrite of the chain C++ program
(https://github.com/gerrymandr/cfp_mcmc), originally by Maria Chikina, Alan
Frieze and Wesley Pegden, for their paper, "Assessing significance in a Markov
chain without mixing" (http://www.pnas.org/content/114/11/2860).

- **Website (with documentation):** https://rundmcmc.readthedocs.io/en/latest/
- **Bug reports:** https://github.com/gerrymandr/RunDMCMC/issues


Example
=======


..code-block:: python
    from gerrychain import MarkovChain, GeographicPartition
    from gerrychain.validity import single_flip_contiguous
    from gerrychain.accept import always_accept
    from gerrychain.proposals import propose_random_flip
    from gerrychain.updaters.compactness import polsby_popper

    pennsylvania = GeographicPartition.from_json_graph("./21/rook.json", assignment="CD113")
    chain = MarkovChain(
        propose_random_flip
        single_flip_contiguous,
        always_accept,
        pennsylvania,
        total_steps=1000
    )

    for partition in chain:
        print(polsby_popper(partition))

Installation
============

To install RunDMCMC, we currently recommend cloning the repository and
installing a development version manually::

    git clone https://github.com/gerrymandr/RunDMCMC.git
    cd RunDMCMC
    python3 setup.py develop