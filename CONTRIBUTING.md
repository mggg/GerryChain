# Contributing to GerryChain

Thanks for your interest in contributing to GerryChain! Contributions of all sizes are welcome,
including bug reports, documentation improvements, tests, examples, and new features.

If you are planning anything larger than a small bug fix or documentation change, please contact
`code@mggg.org` before you start coding. The maintainers can help you align the work with the
current roadmap and target branch.

## Ways to contribute

- Report bugs or confusing behavior.
- Improve or expand documentation and tutorials.
- Add tests for uncovered behavior or regressions.
- Fix bugs, performance problems, or edge cases.
- Propose or implement new proposals, constraints, updaters, metrics, or graph features.

Please search the [issue tracker](https://github.com/mggg/GerryChain/issues) before opening a new
issue. A useful bug report explains what you did, what you expected, what happened instead, and
includes a minimal example when possible.

## Development setup

GerryChain uses:

- [uv](https://docs.astral.sh/uv/) for Python and dependency management
- Make for common development commands
- [Ruff](https://docs.astral.sh/ruff/) for formatting and linting
- [ty](https://github.com/astral-sh/ty) and
  [Pyright](https://github.com/microsoft/pyright) for type checking
- [pytest](https://docs.pytest.org/) for tests
- [pre-commit](https://pre-commit.com/) for local quality checks
- [Sphinx](https://www.sphinx-doc.org/) and [MyST](https://myst-parser.readthedocs.io/) for docs

Recommended setup:

1. Install `uv`.
2. Fork and clone the repository.
3. From the repository root, run `make setup`.

`make setup` installs a managed Python 3.11 environment, syncs every dependency group, and
installs the pre-commit hooks.

If you already have `uv` installed and prefer to run the steps directly, the equivalent setup is:

```bash
uv python install 3.11
UV_MANAGED_PYTHON=1 uv sync --python 3.11 --all-groups
uv run pre-commit install
```

## Contributor workflow

1. Fork the repository and clone your fork locally.
2. Create a descriptive branch from the current target branch.
3. Keep the change focused. Do not bundle unrelated refactors into the same pull request.
4. Add or update tests for behavior changes.
5. Update public documentation when behavior or APIs change.
6. Run the relevant checks locally.
7. Open a pull request that explains the problem, your approach, and how you tested it.

If you are unsure which branch to target, ask the maintainers before opening the pull request.

### Branch naming

Use descriptive branch names such as:

- `fix/recom-region-reselection`
- `feat/add-compactness-updater`
- `docs/update-contributing-guide`

## Running checks locally

The preferred Make targets are:

```bash
make format
make lint
make type-check
make test
make test-all
make precommit
```

`make lint` runs Ruff and both type checkers, so a separate `make type-check` is only needed when
you want to run the type checkers by themselves. `make test-all` includes tests marked as slow.

To run a specific test file through Make:

```bash
make test TEST_PATHS=tests/test_tree.py
```

You can also pass pytest options directly:

```bash
uv run pytest tests/test_tree.py -k bipartition
uv run pytest tests --runslow
uv run pytest tests --cov=gerrychain --cov-report=term-missing
```

Before opening a pull request, also verify that the lockfile is current:

```bash
uv lock --check
```

## Pull request expectations

Before opening a pull request, make sure that:

- the change is scoped to a single topic;
- code, tests, and docs are updated together when needed;
- new behavior and regressions are covered by tests;
- formatting, linting, and type checks pass locally;
- slow tests relevant to the change pass; and
- the description explains the user-facing impact and notable tradeoffs.

Small, focused pull requests are much easier to review and merge than large mixed changes.

## Code style guidelines

GerryChain requires Python 3.11 or later. Follow the current conventions below and avoid
style-only churn in files unrelated to your change.

- Follow the repository tooling first. Ruff defines formatting and baseline lint rules.
- Keep lines at or below 100 characters.
- Add type annotations for function parameters and return values.
- Prefer modern type syntax, such as `str | None` instead of `Optional[str]`.
- Match the import style and structure of the surrounding module.
- Use descriptive `snake_case` names for variables and functions, `PascalCase` for classes, and
  `UPPER_SNAKE_CASE` for module-level constants.
- Keep functions focused and put validation or obvious guard clauses near the top.
- Prefer straightforward control flow and targeted helpers over unnecessary abstraction.
- Preserve useful docstrings and comments when editing older code.
- Use comments sparingly and reserve them for invariants, non-obvious reasoning, or domain context.

### Docstrings

Public classes, functions, and methods should use the repository's Google-style docstrings. Keep
docstrings at or below 100 characters per line and document contracts, defaults, and failure modes.

```python
def population_deviation(population: int, ideal: int) -> float:
    """Return a district's relative population deviation from the ideal.

    Args:
        population (int): District population.
        ideal (int): Ideal district population.

    Returns:
        float: Relative deviation from the ideal population.

    Raises:
        ValueError: If the ideal population is not positive.
    """
    if ideal <= 0:
        raise ValueError("ideal must be positive")
    return (population - ideal) / ideal
```

Use `Args`, `Returns`, and `Raises` when they add information. Add examples when they clarify
non-obvious behavior, not simply to repeat the signature.

## Testing guidelines

Tests are required for behavior changes.

- Add tests under `tests/` near the existing tests for the same module or feature.
- Cover successful behavior, expected failures, and natural edge cases.
- When checking exceptions, verify useful error text with `pytest.raises(..., match=...)`.
- Mark tests that take longer than about ten seconds with `@pytest.mark.slow`.
- Pass an explicit seed or `random.Random` instance in tests involving randomness.
- Do not rely on `PYTHONHASHSEED` or unordered container iteration for reproducibility.
- When changing shared graph behavior, exercise both NetworkX and RustworkX backends when relevant.

The test suite enables GerryChain's runtime integrity checks automatically. Production code should
not assume that those optional checks are enabled.

## Documentation guidelines

If your change affects public behavior, update the relevant documentation with the code. This may
include:

- docstrings under `gerrychain/`;
- narrative Markdown under `docs/`;
- tutorial notebooks under `docs/user/`;
- API reference pages under `docs/api/`; or
- examples and links in `README.md`.

### Notebook-first workflow

Tutorial notebooks under `docs/user/` are the source of truth. Commit them without outputs so
reviews contain only source changes. The pre-commit hook clears outputs and execution counts from
changed notebooks automatically.

The docs build reuses outputs when the notebook source matches the ignored MyST-NB cache under
`docs/_build/`. New or changed notebooks execute in temporary directories with the example
datasets staged. To populate that cache for one notebook without building the site, run:

```bash
make docs-cache-notebooks NOTEBOOKS=docs/user/recom.ipynb
```

Omit `NOTEBOOKS` to execute every tutorial:

```bash
make docs-cache-notebooks
```

### Building and previewing docs

Build the complete site with warnings treated as errors:

```bash
make docs
```

The generated site is written to `docs/_build/`. To serve it locally with automatic rebuilding:

```bash
make docs-serve
```

To force notebook re-execution before a build or preview, set `FRESH=1`. This also works with
`docs` and `docs-cache-notebooks`:

```bash
make docs-serve FRESH=1
```

### Testing docs

Execute Python snippets from Markdown, RST, and `README.md`:

```bash
make docs-test
```

Blocks that cannot run independently must provide a reason:

```md
<!-- docs-test: skip -- fragment; objects are defined earlier in the tutorial -->
```

Shared setup blocks use:

```md
<!-- docs-test: setup -->
```

A page whose blocks are all illustrative fragments can opt out wholesale, with the marker placed
just under the title:

```md
<!-- docs-test: skip-page -- placeholder names and signature-only stubs -->
```

Snippet failures report the original documentation filename and line number. The docs build fails
if a notebook cannot execute, and the test suite rejects notebooks containing committed outputs.

Check external links manually with:

```bash
make docs-linkcheck
```

Pull requests and pushes to `main` execute the notebooks, build the site, run snippet checks, and
upload the built site as a workflow artifact. Read the Docs publishes the site. External link
checking is temporarily manual while the reorganized pages are unpublished.

Documentation dependencies are split into `docs` for building and serving the site and
`docs-exec` for executing notebooks and snippets. The Make targets select the appropriate group.

## Community guidelines

This project follows the Contributor Covenant Code of Conduct. By participating, you agree to
follow the expectations in the
[Code of Conduct](https://github.com/mggg/GerryChain/blob/main/CODE_OF_CONDUCT.md).

## Questions

If anything in the contribution process is unclear, contact `code@mggg.org`. Thanks for helping
make GerryChain better!
