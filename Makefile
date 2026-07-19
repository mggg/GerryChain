# Makefile for managing GerryChain development tasks using 'uv' virtual environment manager.

PYTHON_VERSION = 3.11
VENV_DIR ?= .venv
PKG ?= gerrychain
TEST_PATHS ?= tests
TYPECHECK_PATHS ?= $(PKG) $(TEST_PATHS)
DOCS_PY_PATHS ?= docs/conf.py docs/_clear_notebook_outputs.py \
	docs/_refresh_notebooks.py docs/generate_recom_assets.py
# Tutorial notebooks. Ruff formats the code cells; it ignores the Markdown files alongside them.
NOTEBOOK_PATHS ?= docs/user
DOCS_CACHE_FLAGS = $(if $(filter 1,$(FRESH)),--force)
export UV_MANAGED_PYTHON = 1

.PHONY: help check_prereq setup install install-docs check test test-all type-check format lint \
	precommit docs docs-serve docs-test docs-linkcheck docs-cache-notebooks docs-recom-assets clean

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
	@echo "  docs-cache-notebooks - Execute user-guide notebooks into the ignored docs cache"
	@echo "                  Set FRESH=1 with a docs target to rebuild notebook outputs"
	@echo "  docs-recom-assets - Regenerate the static Gerrymandria images used by recom.ipynb"
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
	@echo "Installing documentation and notebook execution dependencies..."
	uv sync --python $(PYTHON_VERSION) --no-default-groups --group docs --group docs-exec

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
	uv run --group dev ty check $(TYPECHECK_PATHS)
	@echo "Running thorough type checking with Pyright..."
	uv run --group dev pyright $(TYPECHECK_PATHS)

format:
	@echo "Formatting codebase with Ruff..."
	uv run ruff format $(PKG) $(TEST_PATHS) $(DOCS_PY_PATHS) $(NOTEBOOK_PATHS)

lint:
	@echo "Running Ruff..."
	uv run ruff check $(PKG) $(TEST_PATHS) $(DOCS_PY_PATHS)
	$(MAKE) type-check

precommit:
	@echo "Running pre-commit hooks..."
	uv run pre-commit run --all-files

docs: docs-cache-notebooks
	@echo "Building documentation..."
	uv run --no-default-groups --group docs --group docs-exec sphinx-build -E -a -W --keep-going \
		-b dirhtml docs/ docs/_build

docs-serve: docs-cache-notebooks
	@echo "Serving documentation with live reload..."
	uv run --no-default-groups --group docs --group docs-exec \
		sphinx-autobuild -b dirhtml docs/ docs/_build

docs-linkcheck: docs-cache-notebooks
	@echo "Checking documentation links..."
	uv run --no-default-groups --group docs --group docs-exec \
		sphinx-build -E -a -W --keep-going \
		-b linkcheck docs/ docs/_build/linkcheck

# Selects the docs-exec group explicitly so it does not rely on uv's implicit dev group.
docs-test:
	@echo "Executing documentation code snippets..."
	uv run --no-default-groups --group docs --group docs-exec pytest -v --rundocs \
		tests/test_docs_snippets.py

docs-cache-notebooks: install-docs
	@echo "Caching user-guide notebook outputs..."
	uv run --no-default-groups --group docs --group docs-exec \
		python docs/_refresh_notebooks.py $(DOCS_CACHE_FLAGS) $(NOTEBOOKS)

docs-recom-assets: install-docs
	@echo "Regenerating static Gerrymandria images..."
	uv run --no-default-groups --group docs --group docs-exec \
		python docs/generate_recom_assets.py

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
