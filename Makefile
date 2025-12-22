# Makefile for managing GerryChain development tasks using 'uv' virtual environment manager.

PYTHON_VERSION = 3.11
VENV_DIR ?= .venv
PKG ?= gerrychain
TEST_PATHS ?= tests
export UV_MANAGED_PYTHON = 1

.PHONY: help setup install install-docs test lint format precommit docs clean

help:
	@echo "Available targets:"
	@echo "  setup         - Set up environment for full development including dev dependencies and pre-commit hooks"
	@echo "  install       - Install the package"
	@echo "  install-docs  - Install documentation dependencies"
	@echo "  test          - Run the test suite"
	@echo "  lint          - Run code linters"
	@echo "  format        - Format the codebase"
	@echo "  precommit     - Run pre-commit hooks"
	@echo "  docs          - Build the documentation"
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
	uv sync --python $(PYTHON_VERSION) 
	uv sync --all-groups
	uv pip install -e .
	uv run pre-commit install
	@echo ""
	@echo "Development environment setup complete!"

install: check_prereq
	@echo "Installing GerryChain package..."
	uv sync --python $(PYTHON_VERSION)
	uv pip install -e .

install-docs: check_prereq
	@echo "Installing GerryChain package with all just the documentation dependencies..."
	uv sync --python $(PYTHON_VERSION)
	uv sync --group docs
	uv pip install -e .

check:
	$(MAKE) format
	$(MAKE) lint

test:
	@echo "Running test suite..."
	PYTHONHASHSEED=0 uv run pytest -v $(TEST_PATHS)

# Add this in later
# type-check:
# 	@echo "Running type checking with mypy..."
# 	uv run mypy $(PKG) ${TEST_PATHS}

format:
	@echo "Formatting codebase with black..."
	uv run isort $(PKG) $(TEST_PATHS)
	uv run black $(PKG) $(TEST_PATHS)

lint: 
	@echo "Running linters (ruff)..."
	uv run ruff check $(PKG) $(TEST_PATHS)

precommit:
	@echo "Running pre-commit hooks..."
	uv run pre-commit run --all-files

docs: install-docs
	@echo "Building documentation..."
	uv run sphinx-build -b dirhtml docs/ docs/_build

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
