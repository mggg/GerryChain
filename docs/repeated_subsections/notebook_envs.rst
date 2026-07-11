
Using the Virtual Environment in VSCode and Jupyter
---------------------------------------------------

Install ``ipykernel`` in the activated virtual environment before using it in a notebook:

.. code-block:: console

  pip install ipykernel

VSCode
^^^^^^

Open the project folder containing ``.venv`` in VSCode:

.. image:: ../user/images/vscode_tutorial/open_the_folder.png
  :align: center

Install Microsoft's Python and Jupyter extensions:

.. image:: ../user/images/vscode_tutorial/python_extension_vscode.png
  :align: center

.. image:: ../user/images/vscode_tutorial/jupyter_extension_vscode.png
  :align: center

Create and save a file with the ``.ipynb`` extension:

.. image:: ../user/images/vscode_tutorial/Make_a_new_file.png
  :align: center

Use the kernel selector in the notebook to choose the interpreter from the project's ``.venv``:

.. image:: ../user/images/vscode_tutorial/select_kernel_vscode.png
  :align: center

.. image:: ../user/images/vscode_tutorial/select_python_env.png
  :align: center

.. image:: ../user/images/vscode_tutorial/selecting_correct_venv.png
  :align: center

The notebook can now import GerryChain from that environment:

.. image:: ../user/images/vscode_tutorial/show_gerrychain_import.png
  :align: center

Jupyter Lab or Notebook
^^^^^^^^^^^^^^^^^^^^^^^

Install Jupyter and register the activated virtual environment as a kernel. Give each project's
kernel a distinct name if you use several virtual environments:

.. code-block:: console

  pip install jupyter
  python -m ipykernel install --user --name=venv_my_project
  jupyter lab

The registered environment will appear in the kernel list:

.. image:: ../user/images/jupyter_tutorial/jupyter_lab.png
  :align: center

You can inspect registered kernels with ``jupyter kernelspec list``. Create a notebook and select
the project-specific kernel:

.. image:: ../user/images/jupyter_tutorial/make_new_file.png
  :align: center

.. image:: ../user/images/jupyter_tutorial/select_kernel.png
  :align: center

The notebook will then use the GerryChain installation from that virtual environment:

.. image:: ../user/images/jupyter_tutorial/show_import_working.png
  :align: center
