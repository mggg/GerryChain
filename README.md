# GerryChain

[![Code Coverage][coverage-badge]][coverage]
[![Documentation Status][docs-badge]][docs]
[![PyPI Package][pypi-badge]][pypi]

GerryChain is a Python library for building ensembles of districting plans using [Markov chain Monte
Carlo](https://en.wikipedia.org/wiki/Markov_chain_Monte_Carlo). It is developed and maintained by
the [Metric Geometry and Gerrymandering Group](https://www.mggg.org/) and our network of volunteers.
It is distributed under the [3-Clause BSD License](https://opensource.org/licenses/BSD-3-Clause).

The basic workflow is to start with the geometry of an initial plan and generate a large collection
of sample plans for comparison. Usually, we will constrain these sampled plans in such a way that
they perform at least as well as the initial plan according to traditional districting principles,
such as population balance or compactness. Comparing the initial plan to the ensemble provides
quantitative tools for measuring whether or not it is an outlier among the sampled plans.

## Getting started

See our [Getting started guide](https://gerrychain.readthedocs.io/en/latest/user/quickstart/) for
the basics of using GerryChain.

We also highly recommend the resources prepared by Daryl R. DeFord of MGGG for the 2019 MIT IAP
course [Computational Approaches for Political
Redistricting](https://people.csail.mit.edu/ddeford//CAPR.php).

## Useful links

- [Documentation](https://gerrychain.readthedocs.io/en/latest/)
- [Bug reports and feature requests](https://github.com/mggg/gerrychain/issues)
- [Contributions welcome!](https://github.com/mggg/gerrychain/pulls)

## Installation

### Supported Python Versions

The current version of GerryChain requires Python 3.11 or newer.

If you do not have one of these versions installed on you machine, we recommend that you go to the
[Python website](https://www.python.org/downloads/) and download the installer for one of these
versions.[^1]

#### A Note for Windows Users

> If you are using Windows and are new to Python, we recommend that you still install Python using
> the installation package available on the Python website. There are several versions of Python
> available on the Windows Store, but they can be... finicky, and experience seems to suggest that
> downloadable available on the Python website produce better results.
>
> In addition, we recommend that you install the [Windows
> Terminal](https://apps.microsoft.com/detail/9n0dx20hk701) from the Microsoft Store. It is still
> possible to use PowerShell or the Command Prompt, but Windows Terminal tends to be more beginner
> friendly and allows for a greater range of utility than the natively installed terminal options
> (for example, it allows for you to install the more recent version of PowerShell, [PowerShell
> 7](https://docs.microsoft.com/en-us/powershell/scripting/install/installing-powershell), and for
> the use of the Linux Subsystem for Windows).

### Setting Up a Virtual Environment

Once Python is installed on your system, you will want to open the terminal and navigate to the
working directory of your project. Here are some brief instructions for doing so on different
systems:

- **MacOS**: To open the terminal, you will likely want to use the Spotlight Search (the magnifying
  glass in the top right corner of your screen) to find the "Terminal" application (you can also
  access Spotlight Search by pressing "Command (⌘) + Space"). Once you have the terminal open, type
  `cd` followed by the path to your working directory. For example, if you are working on a project
  called `my_project` in your `Documents` folder, you may access by typing the command

  ```console
  cd ~/Documents/my_project
  ```

  into the terminal (here the `~` is a shortcut for your home directory). If you do not know what
  your working directory is, you can find it by navigating to the desired folder in your file
  explorer, and clicking on "Get Info". The path will be labeled "Where" and from there you can copy
  the path to your clipboard and paste it in the terminal.

- **Linux**: Most Linux distributions have the keyboard shortcut `Ctrl + Alt + T` set to open the
  terminal. From there you may navigate to your working directory by typing `cd` followed by the
  path to your working directory. For example, if you are working on a project called `my_project`
  in your `Documents` folder, you may access this via the command

  ```console
  cd ~/Documents/my_project
  ```

  (here the `~` is a shortcut for your home directory). If you do not know what your working
  directory is, you can find it by navigating to the desired folder in your file explorer, and
  clicking on "Properties". The path will be labeled "Location" and from there you can copy the path
  to your clipboard and paste it in the terminal (to paste in the terminal in Linux, you will need
  to use the keyboard shortcut `Ctrl + Shift + V` instead of `Ctrl + V`).

- **Windows**: Open the Windows Terminal and type `cd` followed by the path to your working
  directory. For example, if you are working on a project called `my_project` in your `Documents`
  folder, you may access this by typing the command

  ```console
  cd ~\Documents\my_project
  ```

  into the terminal (here the `~` is a shortcut for your home directory). If you do not know what
  your working directory is, you can find it by navigating to the desired folder in your file
  explorer, and clicking on "Properties". The path will be labeled "Location" and from there you can
  copy the path to your clipboard and paste it in the terminal.

Once you have navigated to your working directory, you will want to set up a virtual environment.
This is a way of isolating the Python packages you install for this project from the packages you
have installed globally on your system. This is useful because it allows you to install different
versions of packages for different projects without worrying about compatibility issues. To set up a
virtual environment, type the following command into the terminal:

```console
python -m venv .venv
```

This will create a virtual environment in your working directory which you can see if you list all
the files in your working directory via the command `ls -a` (`dir` on Windows). Now we need to
activate the virtual environment. To do this, type the following command into the terminal:

- **Windows**: `.venv\Scripts\activate`
- **MacOS/Linux**: `source .venv/bin/activate`

You should now see `(.venv)` at the beginning of your terminal prompt now. This indicates that you
are in the virtual environment, and are now ready to install GerryChain.

To install GerryChain from [PyPI](https://pypi.org/), run `pip install gerrychain` from the command
line.

GerryChain's GIS functions, such as computing adjacencies or reading in shapefiles, work out of the
box: `geopandas` and `shapely` are installed alongside GerryChain, so there is no separate `[geo]`
extra to install.

> **Note**
> If you plan on following through the tutorials present within the remainder of this documentation,
> you will also need to install `matplotlib` from [PyPI](https://pypi.org/). This can also be
> accomplished with a simple invocation of `pip install matplotlib` from the command line.

### Making a Run Reproducible

Each `MarkovChain` owns an independent random number generator, so making a run reproducible takes
one line: pass an integer seed or `random.Random` instance with `MarkovChain(..., rng=2024)`. Random
initial assignments and standalone tree operations accept the same `rng` keyword.

Note that `random.seed` from the standard library does **not** affect GerryChain, and that chain
trajectories do not depend on the `PYTHONHASHSEED` environment variable (older versions of
GerryChain required pinning it, but that is no longer necessary).

> **A note on Jupyter**
>
> If you are using a Jupyter notebook, install `ipykernel` in your virtual environment along with
> either `jupyter notebook` or `jupyterlab`. Then run `jupyter notebook` or `jupyter lab` from your
> working directory while the virtual environment is active. This opens Jupyter in your default
> browser.

[^1]: Of course, if you are using a Linux system, you will either need to use your system's package
    manager or install from source. You may also find luck installing Python directly from the
    package manager if you find installing from source to be troublesome.

[coverage-badge]: https://codecov.io/gh/mggg/GerryChain/branch/main/graph/badge.svg
[coverage]: https://codecov.io/gh/mggg/GerryChain
[docs-badge]: https://readthedocs.org/projects/gerrychain/badge/?version=latest
[docs]: https://gerrychain.readthedocs.io/en/latest
[pypi-badge]: https://badge.fury.io/py/gerrychain.svg
[pypi]: https://pypi.org/project/gerrychain/
