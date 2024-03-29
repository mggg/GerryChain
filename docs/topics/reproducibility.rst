===============
Reproducibility
===============

If you've used GerryChain to do some analysis or research, you may want to ensure that
your analysis is completely repeatable by anyone else on their own computer. This guide
will walk you through the steps required to make that possible.


Share your code on GitHub
-------------------------

Before anyone can run your code, they'll need to find it. We strongly recommend
publishing your source code as a `GitHub`_ repository, and not as a ``.zip`` file on
your personal website. GitHub has a `desktop client`_ that makes this easy, or you
can easily upload and edit your files on the website directly.

.. _`GitHub`: https://github.com/
.. _`desktop client`: https://desktop.github.com/

Make your chains speedily replayable
------------------------------------

It is sometimes desirable to allow others to reproduce or "replay" your chain runs step
by step. In such cirucmstances, we recommend using `pcompress`_ which efficiently and
rapidly stores your MCMC chain runs in a highly-compressed format. It can then be
quickly read-in by `pcompress` at a later date. To setup `pcompress`_, you need to first
`install Cargo`_. Then, you can install `pcompress`_ by installing running ``cargo
install pcompress`` and ``pip install pcompress`` in your terminal.

To use `pcompress`_, you can wrap your ``MarkovChain`` instances with ``Record`` and
pass along the file name you want to save your chain as. For example, this will save
your chain run as ``saved-run.chain``:

.. code-block:: python

    from gerrychain import MarkovChain
    from pcompress import Record

    chain = MarkovChain(
        # chain setup here
    )

    for partition in Record(chain, "saved-run.chain"):
        # normal chain stuff here

Then, if you want to replay your chain run, you can select the same filename and pass
along the graph that was used to generate the chain, along with any updaters that are needed:

.. code-block:: python

    from pcompress import Replay

    for partition in Replay(graph, "saved-run.chain", updaters=my_updaters):
        # normal chain stuff here

The two code samples provided will produce totally equivalent chain runs, up to
reordering. Each step in the replayed chain run will match each step in the recorded
chain run. Furthermore, the replay process will be faster than the original chain
running process and is compatible across future and past releases of GerryChain.


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

.. _`conda`: https://conda.io/projects/conda/en/latest/index.html
.. _`Sharing your environment`: https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#sharing-an-environment
.. _`Creating an environment from an environment.yml file`: https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file


Making Your Environment Reproducible
------------------------------------

If you are working on a project wherein you would like to ensure
particuluar runs are reproducible, it is necessary to invoke

- **MacOS/Linux**: ``export PYTHONHASHSEED=0``
- **Windows**: 

  - PowerShell ``$env:PYTHONHASHSEED=0``
  - Command Prompt ``set PYTHONHASHSEED=0``

before running your code. This will ensure that the hash seed is deterministic
which is important for the replication of spanning trees accross your runs. If you
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
    end of the before the signature bolck. So you should see something like::

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
  either ``jupyternotebook`` or ``jupyterlab``. To install these packages, run
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


Of course, once this is all done, it would be a good idea to save the random seed
that you used somewhere so that others may replicate your work in the future.

.. _`environment variable`: https://en.wikipedia.org/wiki/Environment_variable
.. _`pcompress`: https://github.com/mggg/pcompress
.. _`install Cargo`: https://doc.rust-lang.org/cargo/getting-started/installation.html
