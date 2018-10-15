# Contributing to GerryChain

Thank you for your interest in contributing to GerryChain! If you decide to
participate, use this document as a guide for how to go about it. These are not
strict rules; break them when appropriate.

## How can I contribute?

### Reporting bugs

If you find a bug while using any tools in this repository, consider creating a
[GitHub issue](https://github.com/mggg/GerryChain/issues) documenting the
problem. Be sure to be detailed. Explain what you did, what you expected to
happen, and what actually happened.

### Updating documentation

If you find any documentation that is lacking or in error, submit a pull
request that updates it. Be sure to follow the [documentation
styleguide](#documentation-styleguide).

### Suggesting enhancements

If you have ideas for additional features, consider creating a [GitHub
issue](https://github.com/mggg/GerryChain/issues) documenting the desired
feature. Be sure to be detailed. Explain what the tool currently does (or does
not do), what you would like it to do, and how this benefits users.

### Contributing code (pull requests)

The main way to contribute code to the project is via GitHub pull requests
(PRs). To create a pull request, see the [GitHub
docs](https://help.github.com/articles/creating-a-pull-request/). Be detailed
in the description of your pull request. Explain what your proposed changes do,
and reference any relevant issues.

Be sure to follow the [style guides](#style-guides) for code and documentation.

## Style Guides

### Git commit messages

When writing git commit messages, use the following guidelines:

- Use the present tense ("Update documentation", not "Updated documentation")
- Use the imperative mood ("Fix import", not "Fixes import")
- Limit first line to 72 characters

For further guidelines, see [this
gist](https://gist.github.com/robertpainsi/b632364184e70900af4ab688decf6f53).

### Python styleguide

The recommended styleguide is
[PEP8](https://www.python.org/dev/peps/pep-0008/), the Python standard. Using
the source code linter [flake8](http://flake8.pycqa.org/en/latest/) will
automatically scan your source code for compliance with PEP8.

Below are some highlights of PEP8, but refer to the standard itself for full
details.

- Use 4 spaces per indentation level.

- Use spaces, not tabs.

- Limit lines to 100 characters at maximum.

- Avoid extraneous whitespace, such as in the following situations:

  - `f(x)`, not `f( x )`.
  - `array[x]`, not `array[ x ]`.
  - `if x == 1: print(x)`, not `if x == 1 : print(x)`.

- _Do_ use whitespace around arithmetic operators:

  - `2 + 2`, not `2+2`
  - `x / y`, not `x/y`.

- Write comments as complete sentences with correct punctuation and grammar.

- Write docstrings in
  [reStructuredText](http://docutils.sourceforge.net/rst.html) and in
  accordance with [PEP257](https://www.python.org/dev/peps/pep-0257/).

  - Docstrings are scanned by
    [Sphinx](http://www.sphinx-doc.org/en/master/index.html) to autogenerate
    documentation on our [documentation
    site](http://gerrychain.readthedocs.io/en/latest/).
