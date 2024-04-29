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

.. _`Getting started guide`: https://gerrychain.readthedocs.io/en/latest/user/quickstart/

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

Supported Python Versions
-------------------------

The most recent version of GerryChain (as of April 2024) supports

- Python 3.9
- Python 3.10
- Python 3.11

If you do not have one of these versions installed on you machine, we
recommend that you go to the 
`Python website <https://www.python.org/downloads/>`_ and
download the installer for one of these versions. [1]_

A Note for Windows Users
++++++++++++++++++++++++

  If you are using Windows and are new to Python, we recommend that you
  still install Python using the installation package available on 
  the Python website. There are several versions of Python available
  on the Windows Store, but they can be... finicky, and experience seems
  to suggest that downloadable available on the Python website produce
  better results.

  In addition, we recommend that you install the 
  `Windows Terminal <https://www.microsoft.com/en-us/p/windows-terminal/9n0dx20hk701?activetab=pivot:overviewtab>`_
  from the Microsoft Store. It is still possible to use PowerShell or 
  the Command Prompt, but Windows Terminal tends to be more beginner
  friendly and allows for a greater range of utility than the natively
  installed terminal options (for example, it allows for you to install
  the more recent version of PowerShell, 
  `PowerShell 7 <https://docs.microsoft.com/en-us/powershell/scripting/install/installing-powershell>`_,
  and for the use of the Linux Subsystem for Windows).


Setting Up a Virtual Environment
--------------------------------

Once Python is installed on your system, you will want to open the terminal
and navigate to the working directory of your project. Here are some brief
instructions for doing so on different systems:

- **MacOS**: To open the terminal, you will likely want to use the
  Spotlight Search (the magnifying glass in the top right corner of
  your screen) to find the "Terminal" application (you can also access
  Spotlight Search by pressing "Command (⌘) + Space"). Once you have
  the terminal open, type ``cd`` followed by the path to your working
  directory. For example, if you are working on a project called
  ``my_project`` in your ``Documents`` folder, you may access by typing
  the command

  .. code-block:: console

    cd ~/Documents/my_project
      
  into the terminal (here the ``~`` is a shortcut for your home directory).
  If you do not know what your working directory is, you can find it by
  navigating to the desired folder in your file explorer, and clicking
  on "Get Info". The path will be labeled "Where" and from there you
  can copy the path to your clipboard and paste it in the terminal.


- **Linux**: Most Linux distributions have the keyboard shortcut
  ``Ctrl + Alt + T`` set to open the terminal. From there you may navigate
  to your working directory by typing ``cd`` followed by the path to your
  working directory. For example, if you are working on a project called
  ``my_project`` in your ``Documents`` folder, you may access this via
  the command
  
  .. code-block:: console

    cd ~/Documents/my_project

  (here the ``~`` is a shortcut for your home directory). If you do not
  know what your working directory is, you can find it by navigating to
  the desired folder in your file explorer, and clicking on "Properties".
  The path will be labeled "Location" and from there you can copy the path
  to your clipboard and paste it in the terminal (to paste in the terminal
  in Linux, you will need to use the keyboard shortcut ``Ctrl + Shift + V``
  instead of ``Ctrl + V``).

- **Windows**: Open the Windows Terminal and type ``cd`` followed by the
  path to your working directory. For example, if you are working on a
  project called ``my_project`` in your ``Documents`` folder, you may
  access this by typing the command

  .. code-block:: console

    cd ~\Documents\my_project

  into the terminal (here the ``~`` is a shortcut for your home directory). 
  If you do not know what your working directory is,
  you can find it by navigating to the desired folder in your file
  explorer, and clicking on "Properties". The path will be labeled
  "Location" and from there you can copy the path to your clipboard
  and paste it in the terminal.


Once you have navigated to your working directory, you will want to
set up a virtual environment. This is a way of isolating the Python
packages you install for this project from the packages you have
installed globally on your system. This is useful because it allows
you to install different versions of packages for different projects
without worrying about compatibility issues. To set up a virtual
environment, type the following command into the terminal:

.. code-block:: console

  python -m venv .venv

This will create a virtual environment in your working directory which
you can see if you list all the files in your working directory via
the command ``ls -a`` (``dir`` on Windows). Now we need to activate the
virtual environment. To do this, type the following command into the
terminal:

- **Windows**: ``.venv\Scripts\activate``
- **MacOS/Linux**: ``source .venv/bin/activate``

You should now see ``(.venv)`` at the beginning of your terminal prompt
now. This indicates that you are in the virtual environment, and are now
ready to install GerryChain.

To install GerryChain from PyPI_, run ``pip install gerrychain`` from
the command line. 

If you plan on using GerryChain's GIS functions, such as computing
adjacencies or reading in shapefiles, then run
``pip install gerrychain[geo]`` from the command line.

This approach sometimes fails due to compatibility issues between our
different Python GIS dependencies, like ``geopandas``, ``pyproj``,
``fiona``, and ``shapely``. If you run into this issue, try installing
the dependencies using the `geo_settings.txt <https://github.com/mggg/GerryChain/tree/main/docs/geo_settings.txt>`_
file. To do this, run ``pip install -r geo_settings.txt`` from the
command line.

.. note::

  If you plan on following through the tutorials present within the
  remainder of this documentation, you will also need to install
  ``matplotlib`` from PyPI_. This can also be accomplished with
  a simple invocation of ``pip install matplotlib`` from the command
  line.

.. _PyPI: https://pypi.org/
.. [1] Of course, if you are using a Linux system, you will either need to use your
  system's package manager or install from source. You may also find luck installing
  Python directly from the package manager if you find installing from source to be
  troublesome.

Making an Environment Reproducible
----------------------------------

If you are working on a project wherein you would like to ensure
particular runs are reproducible, it is necessary to invoke

- **MacOS/Linux**: ``export PYTHONHASHSEED=0``
- **Windows**: 

  - PowerShell ``$env:PYTHONHASHSEED=0``
  - Command Prompt ``set PYTHONHASHSEED=0``

before running your code. This will ensure that the hash seed is deterministic
which is important for the replication of spanning trees across your runs. If you
would prefer to not have to do this every time, then you need to modify the
activation script for the virtual environment. Again, this is different depending
on your operating system:

- **MacOS/Linux**: Open the file ``.venv/bin/activate`` located in your working
  directory using your favorite text editor
  and add the line ``export PYTHONHASHSEED=0`` after the ``export PATH`` command. 
  So you should see something like:: 

    _OLD_VIRTUAL_PATH="$PATH"
    PATH="$VIRTUAL_ENV/Scripts:$PATH"
    export PATH

    export PYTHONHASHSEED=0
  
  Then, verify that the hash seed is set to 0 in your Python environment by
  running ``python`` from the command line and typing 
  ``import os; print(os.environ['PYTHONHASHSEED'])``.

- **Windows**: To be safe, you will need to modify 3 files within your virtual
  environment:

  - ``.venv\Scripts\activate``: Add the line ``export PYTHONHASHSEED=0`` after
    the ``export PATH`` command. So you should see something like:: 

      _OLD_VIRTUAL_PATH="$PATH"
      PATH="$VIRTUAL_ENV/Scripts:$PATH"
      export PATH

      export PYTHONHASHSEED=0

  - ``.venv\Scripts\activate.bat``: Add the line ``set PYTHONHASHSEED=0`` to the
    end of the file. So you should see something like::

      if defined _OLD_VIRTUAL_PATH set PATH=%_OLD_VIRTUAL_PATH%
      if not defined _OLD_VIRTUAL_PATH set _OLD_VIRTUAL_PATH=%PATH%

      set PATH=%VIRTUAL_ENV%\Scripts;%PATH%
      rem set VIRTUAL_ENV_PROMPT=(.venv) 
      set PYTHONHASHSEED=0

  - ``.venv\Scripts\Activate.ps1``: Add the line ``$env:PYTHONHASHSEED=0`` to the
    end of the before the signature block. So you should see something like::

      # Add the venv to the PATH
      Copy-Item -Path Env:PATH -Destination Env:_OLD_VIRTUAL_PATH
      $Env:PATH = "$VenvExecDir$([System.IO.Path]::PathSeparator)$Env:PATH"

      $env:PYTHONHASHSEED=0

      # SIG # Begin signature block

After you have made these changes, verify that the hash seed is set to 0 in your
Python environment by running ``python`` from the command line and typing 
``import os; print(os.environ['PYTHONHASHSEED'])`` in the Python prompt.

.. admonition:: A Note on Jupyter
  :class: note

  If you are using a jupyter notebook, you will need to make sure that you have
  installed the ``ipykernel`` package in your virtual environment as well as
  either ``jypyternotebook`` or ``jupyterlab``. To install these packages, run
  ``pip install <package-name>`` from the command line. Then, to use the virtual
  python environment in your jupyter notebook, you need to invoke
  
  .. code-block:: console

    jupyter notebook

  or

  .. code-block:: console

    jupyter lab

  from the command line of your working directory *while your virtual environment
  is activated*. This will open a jupyter notebook in your default browser. You may
  then check that the hash seed is set to 0 by running the following code in a cell
  of your notebook:

  .. code-block:: python

    import os
    print(os.environ['PYTHONHASHSEED'])
