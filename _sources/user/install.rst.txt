.. include:: ./install_header.rst

.. admonition:: A Note For Windows Users
  :class: note

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


.. _virtual-envs:

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

You should now see ``(.venv)`` at the beginning of your terminal prompt. 
This indicates that you are in the virtual environment, and are now
ready to install GerryChain.

To install GerryChain from PyPI_, run ``pip install gerrychain`` from
the command line. 


.. note::

  If you plan on following through the tutorials present within the
  remainder of this documentation, you will also need to install
  ``matplotlib`` from PyPI_. This can also be accomplished with
  a simple invocation of ``pip install matplotlib`` from the command
  line.

.. _PyPI: https://pypi.org/


.. include:: ../repeated_subsections/reproducible_envs.rst
