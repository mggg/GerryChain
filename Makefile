# Makefile for managing GerryChain development tasks using 'uv' virtual environment manager.

PYTHON_VERSION = 3.11
VENV_DIR ?= .venv
PKG ?= gerrychain
TEST_PATHS ?= tests
TYPECHECK_PATHS ?= $(PKG) tests/typing_assertions.py
DOCS_PY_PATHS ?= docs/conf.py docs/_refresh_notebooks.py docs/generate_recom_assets.py
export UV_MANAGED_PYTHON = 1

.PHONY: help check_prereq setup install install-docs check test test-all type-check format lint \
	precommit docs docs-serve docs-test docs-linkcheck docs-refresh-notebooks \
	docs-check-notebooks clean

help:
	@echo "Available targets:"
	@echo "  setup         - Set up environment for full development including dev dependencies and pre-commit hooks"
	@echo "  install       - Install the package"
	@echo "  install-docs  - Install documentation dependencies"
	@echo "  test          - Run the test suite"
	@echo "  test-all      - Run the test suite including slow tests"
	@echo "  lint          - Run Ruff and both type checkers"
	@echo "  type-check    - Run ty, then Pyright"
	@echo "  format        - Format the codebase"
	@echo "  precommit     - Run pre-commit hooks"
	@echo "  docs          - Build the documentation (warnings are errors)"
	@echo "  docs-serve    - Serve the documentation locally with live reload"
	@echo "  docs-test     - Execute the Python code blocks in the documentation"
	@echo "  docs-linkcheck - Check external links in the documentation"
	@echo "  docs-refresh-notebooks - Re-execute the user-guide notebooks and refresh committed outputs"
	@echo "  docs-check-notebooks - Verify the committed notebook outputs are fresh"
	@echo "  clean         - Clean build artifacts"


check_prereq:
	@echo "Checking prerequisites..."
	@if ! command -v uv > /dev/null 2>&1; then \
		echo "Error: 'uv' is not installed. Please install it first using the following command:"; \
		echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 1; \
	fi
	@echo "'uv' is installed."

setup: check_prereq
	@echo "Setting up the development environment for GerryChain..."
	@echo
	uv python install $(PYTHON_VERSION)
	@echo "Creating virtual environment and installing dev dependencies..."
	uv sync --python $(PYTHON_VERSION) --all-groups
	uv run pre-commit install
	@echo ""
	@echo "Development environment setup complete!"

install: check_prereq
	@echo "Installing GerryChain package..."
	uv sync --python $(PYTHON_VERSION)

install-docs: check_prereq
	@echo "Installing GerryChain package with all just the documentation dependencies..."
	uv sync --python $(PYTHON_VERSION) --no-default-groups --group docs

check:
	$(MAKE) format
	$(MAKE) lint

test:
	@echo "Running test suite..."
	uv run pytest -v $(TEST_PATHS)

test-all:
	@echo "Running test suite (including slow tests)..."
	uv run pytest -v --runslow $(TEST_PATHS)

type-check:
	@echo "Running fast type checking with ty..."
	uv run --group frm ty check $(TYPECHECK_PATHS)
	@echo "Running thorough type checking with Pyright..."
	uv run --group frm pyright $(TYPECHECK_PATHS)

format:
	@echo "Formatting codebase with Ruff..."
	uv run ruff format $(PKG) $(TEST_PATHS) $(DOCS_PY_PATHS)

lint:
	@echo "Running Ruff..."
	uv run ruff check $(PKG) $(TEST_PATHS) $(DOCS_PY_PATHS)
	$(MAKE) type-check

precommit:
	@echo "Running pre-commit hooks..."
	uv run pre-commit run --all-files

docs: install-docs
	@echo "Building documentation..."
	uv run --no-default-groups --group docs sphinx-build -E -a -W --keep-going \
		-b dirhtml docs/ docs/_build

docs-serve: install-docs
	@echo "Serving documentation with live reload..."
	uv run --no-default-groups --group docs sphinx-autobuild -b dirhtml docs/ docs/_build

docs-linkcheck: install-docs
	@echo "Checking documentation links..."
	uv run --no-default-groups --group docs sphinx-build -E -a -W --keep-going \
		-b linkcheck docs/ docs/_build/linkcheck

# Selects the docs-exec group explicitly so it does not rely on uv's implicit dev group.
docs-test:
	@echo "Executing documentation code snippets..."
	uv run --no-default-groups --group docs-exec pytest -v --rundocs \
		tests/test_docs_snippets.py

# Re-execute user-guide notebooks and rewrite their committed outputs. Pass NOTEBOOKS=...
# to refresh a subset, e.g. `make docs-refresh-notebooks NOTEBOOKS=docs/user/recom.ipynb`.
docs-refresh-notebooks:
	@echo "Refreshing user-guide notebooks..."
	uv run --no-default-groups --group docs-exec python docs/_refresh_notebooks.py $(NOTEBOOKS)

docs-check-notebooks:
	@echo "Checking that committed notebook outputs are fresh..."
	uv run --no-default-groups --group docs-exec python docs/_refresh_notebooks.py --check $(NOTEBOOKS)

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build/ \
		dist/ \
		*.egg-info \
		.pytest_cache/ \
		.mypy_cache/ \
		.ruff_cache/ \
		docs/_build/ \
		$(VENV_DIR) \
		.vscode/ \
		.ipynb_checkpoints/ \
		docs/build/
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Clean complete."
