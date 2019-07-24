===============
Reproducibility
===============

If you've used GerryChain to do some analysis or research, you may want to ensure that your analysis is
completely repeatable by anyone else on their own computer. This guide will walk you through the steps
required to make that possible.


Share your code on GitHub
-------------------------

Before anyone can run your code, they'll need to find it. We strongly recommend publishing your source code
as a `GitHub`_ repository, and not as a ``.zip`` file on your personal website. GitHub has a
`desktop client`_ that makes this easy.

.. _`GitHub`: https://github.com/
.. _`desktop client`: https://desktop.github.com/


Use the same versions of all of your dependencies
-------------------------------------------------

You will want to make sure that anyone who tries to repeat your analysis by
running your code will have the exact same versions of all of the software and packages
that you use, including the same version of Python.

The easiest way to do this is to use `conda`_ to manage all of your dependencies.
You can use conda to export an ``environment.yml`` file that anyone can use to replicate your
environment by running the command ``conda env create -f environment.yml``. For instructions on
how to do this, see `Sharing your environment`_ and `Creating an environment from an environment.yml file`_
in the conda documentation.

If you've published your code on GitHub, it is a good idea to include your ``environment.yml``
file in the root folder of your code repository.

.. _`Sharing your environment`: https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#sharing-an-environment
.. _`Creating an environment from an environment.yml file`: https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file


Import ``random`` from ``gerrychain.random``
--------------------------------------------

The submodule ``gerrychain.random`` is the single place where GerryChain imports the built-in Python
module ``random`` and sets a random seed. This makes sure that all randomness is used *after* the seed
is set. If you use the ``random`` module anywhere in your own code (say, in your own proposal function),
replace the line ``import random`` with ``from gerrychain.random import random``. This will ensure
that your code uses the same random seed as GerryChain.

GerryChain sets a random seed of ``2018`` after it imports ``random``. If you wish to use a different
random seed, set it immediately after importing ``random`` from ``gerrychain.random``, and *before* you
import anything else. That will look like this:


.. code-block:: python

    from gerrychain.random import random
    random.seed(12345678)

    from gerrychain import MarkovChain, Partition
    # and so on...


Set ``PYTHONHASHSEED=0``
------------------------

In addition to the randomness provided by the ``random`` module, Python uses a random
seed for its hashing algorithm, which affects how objects are stored in sets and dictionaries.
This must happen the same way every time in order for GerryChain runs to be repeatable.

The way to accomplish this is to set the `environment variable`_ ``PYTHONHASHSEED`` to ``0``.

If you are using conda_ for managing packages, dependencies, and environments, you can
`save environment variables in your conda environment`_.

Otherwise, in macOS or Linux environments you can accomplish this by running the command ``export PYTHONHASHSEED=0``
in the Terminal or bash shell before running your code.

In a Windows 10 environment using PowerShell, you can accomplish this by running ``$env:PYTHONHASHSEED=0``
before running your code.


.. _`environment variable`: https://en.wikipedia.org/wiki/Environment_variable
.. _conda: https://conda.io/en/master/
.. _`save environment variables in your conda environment`: https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#saving-environment-variables
