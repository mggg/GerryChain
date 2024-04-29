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

The best way to do this is to create a `virtual environment <../user/install.html#virtual-envs>`_ 
and then save all of the dependencies to a file. This will allow anyone to recreate the
exact same environment that you used to run your code. To save the packages that are in
your current virtual environment, simply run

.. code:: console 

  pip freeze > requirements.txt

and this will save the versions of all of your packages to a file called
``requirements.txt``. You can then share this file with anyone who wants to run your code,
and they can create the same virtual environment by running

.. code:: console

  pip install -r requirements.txt

Of course, you will both be responsible for making sure that your virtual environments
have the same ``PYTHONHASHSEED`` set. How to do this is detailed in the next section.


.. include:: ../repeated_subsections/reproducible_envs.rst

.. _`pcompress`: https://github.com/mggg/pcompress
.. _`install Cargo`: https://doc.rust-lang.org/cargo/getting-started/installation.html
