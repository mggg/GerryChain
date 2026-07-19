# Installation

The programming environment used by GerryChain is based on Python. It takes advantage of the robust
Python ecosystem for data analysis, data structures, plotting and more.

In this section we will walk you through setting up a Python environment, installing the needed
Python packages, installing VSCode and Jupyter Lab, and validating that everything is ready to go.

## Supported Python Versions

The most recent version of GerryChain supports

- Python 3.11
- Python 3.12
- Python 3.13
- Python 3.14

If you install GerryChain with uv, as recommended below, you do not need to install any of these
yourself. uv will download a suitable version for you.

(virtual-envs)=

## Setting Up Your Environment

Whichever method you use, you will want to work inside a virtual environment. This is a way of
isolating the Python packages you install for this project from the packages you have installed
globally on your system. It lets you install different versions of packages for different projects
without worrying about compatibility issues.

Start by opening the terminal and navigating to the working directory of your project. Here are
some brief instructions for doing so on different systems:

- **MacOS**: To open the terminal, you will likely want to use the
  Spotlight Search (the magnifying glass in the top right corner of
  your screen) to find the "Terminal" application (you can also access
  Spotlight Search by pressing "Command (⌘) + Space"). Once you have
  the terminal open, type `cd` followed by the path to your working
  directory. For example, if you are working on a project called
  `my_project` in your `Documents` folder, you may access by typing
  the command

  ```console
  cd ~/Documents/my_project
  ```

  into the terminal (here the `~` is a shortcut for your home directory).
  If you do not know what your working directory is, you can find it by
  navigating to the desired folder in your file explorer, and clicking
  on "Get Info". The path will be labeled "Where" and from there you
  can copy the path to your clipboard and paste it in the terminal.

- **Linux**: Most Linux distributions have the keyboard shortcut
  `Ctrl + Alt + T` set to open the terminal. From there you may navigate
  to your working directory by typing `cd` followed by the path to your
  working directory. For example, if you are working on a project called
  `my_project` in your `Documents` folder, you may access this via
  the command

  ```console
  cd ~/Documents/my_project
  ```

  (here the `~` is a shortcut for your home directory). If you do not
  know what your working directory is, you can find it by navigating to
  the desired folder in your file explorer, and clicking on "Properties".
  The path will be labeled "Location" and from there you can copy the path
  to your clipboard and paste it in the terminal (to paste in the terminal
  in Linux, you will need to use the keyboard shortcut `Ctrl + Shift + V`
  instead of `Ctrl + V`).

- **Windows**: Open the Windows Terminal and type `cd` followed by the
  path to your working directory. For example, if you are working on a
  project called `my_project` in your `Documents` folder, you may
  access this by typing the command

  ```console
  cd ~\Documents\my_project
  ```

  into the terminal (here the `~` is a shortcut for your home directory).
  If you do not know what your working directory is,
  you can find it by navigating to the desired folder in your file
  explorer, and clicking on "Properties". The path will be labeled
  "Location" and from there you can copy the path to your clipboard
  and paste it in the terminal.

### Using uv (recommended)

We recommend [uv](https://docs.astral.sh/uv/), which manages both Python itself and your project's
packages. When using uv it is not necessary to have Python installed on the machine: the Astral
team ships stand-alone versions of Python that uv can download and use automagically. This is
particularly helpful for Windows users, since Windows has several ways of installing Python, each
of which comes with its own quirks.

Install uv by following the
[official installation instructions](https://docs.astral.sh/uv/getting-started/installation/),
then create a project and add GerryChain to it:

```console
uv init my_project
cd my_project
uv add gerrychain matplotlib
```

This creates a `my_project` directory containing a `.venv` environment and a `pyproject.toml`
recording what you installed, and it downloads a suitable Python if you do not already have one.
`matplotlib` is included because the tutorials in this documentation plot their results.

You do not need to activate anything. Prefix commands with `uv run` and uv will use the project's
environment:

```console
uv run python my_script.py
```

This is worth getting into the habit of, because forgetting to activate an environment is far and
away the most common cause of confusing "module not found" errors.

To use the development version from GitHub instead of the latest release, point uv at the
repository:

```console
uv add git+https://github.com/mggg/GerryChain
```

For more information on managing python projects with uv, see the
[uv project documentation](https://docs.astral.sh/uv/concepts/projects/).

### Using pip and venv

If you would rather not use uv, you can manage the environment yourself. You will need to install
Python first from the [Python website](https://www.python.org/downloads/), choosing one of the
supported versions listed above.

:::{admonition} A Note For Windows Users
:class: note

If you are using Windows and are new to Python, we recommend installing Python using the
installation package available on the Python website. There are several versions of Python
available on the Windows Store, but they can be finicky, and experience suggests that the
downloadable version from the Python website produces better results. This Python source
sensitivity is the main reason that we recommend using uv since it resolves dependency issues
for you.

In addition, we recommend that you install the
[Windows Terminal](https://apps.microsoft.com/detail/9n0dx20hk701)
from the Microsoft Store. It is still possible to use PowerShell or the Command Prompt, but Windows
Terminal tends to be more beginner friendly and allows for a greater range of utility than the
default terminal options (for example, it allows for you to install the more recent version of
PowerShell,
[PowerShell 7](https://docs.microsoft.com/en-us/powershell/scripting/install/installing-powershell),
and for the use of the Linux Subsystem for Windows).
:::

To set up a virtual environment, type the following command into the terminal:

```console
python -m venv .venv
```

This will create a virtual environment in your working directory which
you can see if you list all the files in your working directory via
the command `ls -a` (`dir` on Windows). Now we need to activate the
virtual environment. To do this, type the following command into the
terminal:

- **Windows**: `.venv\Scripts\activate`
- **MacOS/Linux**: `source .venv/bin/activate`

You should now see `(.venv)` at the beginning of your terminal prompt.
This indicates that you are in the virtual environment, and are now
ready to install GerryChain.

To install GerryChain and the plotting library used by the tutorials from [PyPI], run:

```console
pip install gerrychain matplotlib
```

[pypi]: https://pypi.org/

## Checking Your Installation

Before moving on, it is worth confirming that everything landed where you expect.

If you are using uv, run these from your project directory. If you set the environment up yourself,
run them in the terminal where you activated it and drop the `uv run` prefix.

**1. Python is new enough.** GerryChain requires Python 3.11 or newer:

```console
uv run python --version
```

**2. You are using the project's Python.** Under uv this is handled for you, but it is the single
most common source of confusing errors when managing an environment by hand, so it is worth
checking rather than trusting the `(.venv)` prompt:

```console
uv run python -c "import sys; print(sys.executable)"
```

The path printed must be inside your project's `.venv` directory. If it points somewhere else and
you are not using uv, the environment is not active; activate it again using the command for your
system above.

**3. GerryChain imports and works.** This prints the version you have installed, then builds a
small graph and splits it into two districts, exercising the pieces everything else is built on:

```console
uv run python -c "import importlib.metadata as md, networkx; from gerrychain import Graph, Partition; print('gerrychain', md.version('gerrychain')); g = Graph.from_networkx(networkx.path_graph(4)); p = Partition(g, {0: 'a', 1: 'a', 2: 'b', 3: 'b'}); print('built a partition with', len(p.parts), 'districts')"
```

After the version, you should see:

```console
built a partition with 2 districts
```

It is worth noting which version this reports. The guides in this documentation describe the
current release, so if the version is older than you expected, that is usually the explanation for
an API that does not match what you are reading here.

A `ModuleNotFoundError` here means GerryChain was installed into a different environment than the
one you are running, which check 2 will usually explain.

**4. The tutorial extras are present.** The guides plot their results, so they also need
`matplotlib`:

```console
uv run python -c "import matplotlib; print(matplotlib.__version__)"
```

If all four checks pass, your environment is working. The next section covers using it from an
editor or notebook.

:::{note}
If something fails and the messages above do not explain it, please
[open an issue](https://github.com/mggg/GerryChain/issues) describing what you ran and what you saw.
Environment problems are common and we would rather fix the instructions than have you work around
them.
:::

## Using Your Environment in VSCode and Jupyter

### VSCode

VSCode needs `ipykernel` in the environment to run notebooks against it:

```console
uv add ipykernel
```

Or, if you are managing the environment yourself, install it into the activated virtual
environment:

```console
pip install ipykernel
```

Open the project folder containing `.venv` in VSCode:

```{image} images/vscode_tutorial/open_the_folder.png
:align: center
```

Install Microsoft's Python and Jupyter extensions:

```{image} images/vscode_tutorial/python_extension_vscode.png
:align: center
```

```{image} images/vscode_tutorial/jupyter_extension_vscode.png
:align: center
```

Create and save a file with the `.ipynb` extension:

```{image} images/vscode_tutorial/Make_a_new_file.png
:align: center
```

Use the kernel selector in the notebook to choose the interpreter from the project's `.venv`:

```{image} images/vscode_tutorial/select_kernel_vscode.png
:align: center
```

```{image} images/vscode_tutorial/select_python_env.png
:align: center
```

```{image} images/vscode_tutorial/selecting_correct_venv.png
:align: center
```

The notebook can now import GerryChain from that environment:

```{image} images/vscode_tutorial/show_gerrychain_import.png
:align: center
```

### Jupyter Lab or Notebook

Add Jupyter to the project. It brings `ipykernel` with it, so there is no need to add that
separately:

```console
uv add jupyter
uv run jupyter lab
```

Launched this way, Jupyter already sees the project's environment, listed as the default Python
kernel. You only need to register a named kernel if you want to reach this project from a Jupyter
installed elsewhere. Give each project's kernel a distinct name if you work on several of them:

```console
uv run python -m ipykernel install --user --name=venv_my_project
```

If you are managing the environment yourself, the equivalent from the activated virtual environment
is:

```console
pip install jupyter
python -m ipykernel install --user --name=venv_my_project
jupyter lab
```

The registered environment will appear in the kernel list:

```{image} images/jupyter_tutorial/jupyter_lab.png
:align: center
```

You can inspect registered kernels with `jupyter kernelspec list`. Create a notebook and select
the project-specific kernel:

```{image} images/jupyter_tutorial/make_new_file.png
:align: center
```

```{image} images/jupyter_tutorial/select_kernel.png
:align: center
```

The notebook will then use the GerryChain installation from that virtual environment:

```{image} images/jupyter_tutorial/show_import_working.png
:align: center
```

### Confirming the Notebook Uses the Right Environment

The terminal checks above cannot catch a notebook that is running against a different interpreter,
which is what produces the classic "it works in the terminal but `import gerrychain` fails in
Jupyter" problem. Run this in a notebook cell:

```python
import sys

print(sys.executable)
```

The path must match the one printed by check 2 in
[Checking Your Installation](#checking-your-installation). If it does not, the notebook is using a
different kernel: reselect the project kernel, and if it is missing, register it again using the
`ipykernel install` command above.

## Next Steps

Your environment is ready. Head to the [Getting started guide](./quickstart.ipynb) to build your
first Markov chain in GerryChain!
