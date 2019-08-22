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

    conda update -n base conda
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
