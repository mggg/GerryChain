==========================
Contributing to GerryChain
==========================

Thank you for your interest in contributing to GerryChain! This document provides
guidelines for contributing to the GerryChain project. All contributions and 
feedback are welcome and appreciated 😊.


Quick Start
===========

1. **Fork the repository** on GitHub.
2. **Clone your fork locally**.
3. **Configure the upstream repo** ``git remote add upstream https://github.com/mggg/GerryChain.git``
4. **Create a new branch** for your contribution ``git checkout -b my-new-feature``.
5. **Make your changes** and commit them ``git commit -am 'Add some feature'``.
6. **Run Tests and Linter** with ``pytest --runslow tests/`` and ``flake8 gerrychain/``.
7. **Pull the latest changes from upstream** and rebase your branch if necessary.
8. **Push your branch** to GitHub ``git push origin my-new-feature``.
9. **Open a Pull Request** on GitHub.

Prerequisites
=============

Before you can contribute to GerryChain, you need the following installed on your machine:

- **Python (3.9 or later)**: GerryChain is written in Python, so you'll need Python installed.
- **Git**: Version control is essential for contributing to open-source projects.

We also recommend that for any development work, you use a python virtual environment to
manage dependencies. For more information on setting up your environment, please see
the `installation <../user/install.html>`_ section of the documentation. However, rather
than using the ``pip install gerrychain`` command, you should instead install the package
from source by running ``pip install -e .`` from the root of the repository.

Contributing Guidelines
=======================

**Coding Standards**: GerryChain follows PEP 8 guidelines for coding style, so we
ask that any contributors do the same to ensure that the codebase is consistent. For
more information, see the `PEP 8 Style Guide <https://www.python.org/dev/peps/pep-0008/>`_.

**Writing Tests**: If you write a new feature, please make sure that it is
included in a test somewhere. GerryChain uses pytest for testing and has a
special ``--runslow`` flag for tests that take a long time to run. Please make
sure to check against these slow tests as well before submitting a PR. For any
tests that you write that run for longer than ~10 seconds, please mark them with
the ``@pytest.mark.slow`` decorator.

**Documentation**: For any new features that you add, please make sure to include
a comprehensive docstring. We have a defined format for docstrings that we use
throughout the codebase, so please make sure that any additions are consistent
with that format.

Pull Request Process
--------------------

1. Ensure your branch is up to date with the ``main`` branch and that the tests are passing.
2. Open a pull request against the ``main`` branch of the GerryChain repository. With a detailed comment explaining the changes you made and the reasoning behind them.
3. The project maintainers will review your changes and provide feedback.
 

Community Guidelines
====================

We follow an adaptation of the Contributor Covenant Code of Conduct, which, 
in essence, means that we expect community members to

- **Be respectful** of different viewpoints and experience levels.
- **Gracefully accept constructive criticism**.
- **Focus on what is best for the community**.

For more detailed information about our community guidelines, please see the
`Code of Conduct <https://github.com/mggg/GerryChain/blob/main/CODE_OF_CONDUCT.md>`_ 
page of the main repository.


Thank You
=========

Thank you for contributing to GerryChain! We appreciate all the time and
effort that you put into making this package the best that it can be!
