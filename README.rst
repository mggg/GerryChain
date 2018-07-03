===============================
RunDMCMC
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


This code implements Monte-Carlo exploration of districting plans, exploring
the space around an initial districting plan to give some idea of the degree of
gerrymandering. It is a Python rewrite of the chain C++ program
(https://github.com/gerrymandr/cfp_mcmc), originally by Maria Chikina, Alan
Frieze and Wesley Pegden, for their paper, "Assessing significance in a Markov
chain without mixing" (http://www.pnas.org/content/114/11/2860)


Installation
============

Ideally, the following conda command will work:

``conda install -c gerrymandr rundmcmc``

Should our release system be broken, cloning this repository and manually
running ``setup.py`` will also work::

    git clone https://github.com/gerrymandr/RunDMCMC.git
    cd RunDMCMC
    python3 setup.py install


Using in an interactive python session
======================================

Here's how you can use RunDMCMC in an interactive python session.
Navigate to the RunDMCMC/rundmcmc folder in a terminal, and then run an `ipython` or `python` command
to open an interactive session. Alternatively, this should work in the terminal window in Spyder.

Now we can start playing with Markov chains! First we'll import some things.

.. code-block:: python

    from rundmcmc.grid import Grid

The `Grid` class is a little helper class for playing around with grid examples.

.. code-block:: python

    grid = Grid((20,20))    # Make a 20x20 grid
    print(grid)

You should see a grid made out of 0's, 1's, 2's, and 3's. By default, the `Grid` is partitioned into
four equal quadrants.

Running a chain
---------------

Now we can configure and run a `MarkovChain`.

.. code-block:: python

    from rundmcmc.chain import MarkovChain
    from rundmcmc.proposals import propose_random_flip
    from rundmcmc.validity import Validator, contiguous
    from rundmcmc.accept import always_accept

    is_valid = Validator([contiguous])

We'll configure a chain starting with `grid`, using the regular boundary flip proposal,
validating that the districts are connected, and always accepting if the proposal is valid.

.. code-block:: python

    chain = MarkovChain(propose_random_flip, is_valid, always_accept, grid, total_steps=1000)

The `MarkovChain` in RunDMCMC is just a python generator. This means we can do a simple
for loop over all the states in the chain.

.. code-block:: python

    for partition in chain:
        print(partition)

This should output a bunch of grids like before, but with the districts changing over time.

Making a histogram
------------------

Now we can make a histogram! The Grid class comes with a fake 'population' attribute. This
attribute can be accessed as `grid['population']`. It is a dictionary from the districts
to their populations.
We'll make a histogram of the minimum district population at each step in the chain.

We'll import `matplotlib` to make the histogram, but feel free to use your favorite alternative.

.. code-block:: python

    import matplotlib.pyplot as plt

We can generate the data for our histogram using a simple list comprehension:

.. code-block:: python

    data = [min(partition['population'].values()) for partition in chain]

.. code-block:: python

    plt.hist(data)
    plt.show()

The histogram should pop up in a new window. Yay!