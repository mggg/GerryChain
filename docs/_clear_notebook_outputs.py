"""Remove generated outputs and execution counts from notebooks."""

import sys
from pathlib import Path

import nbformat


# Kernel metadata a local Jupyter session stamps onto a notebook. It must match what
# docs/_refresh_notebooks.py normalizes to before caching, or the docs build recomputes a
# different cache key, misses the pre-built cache, and re-executes the notebook in a CWD without
# the sample data (which fails on CI). Keeping the committed metadata pinned here avoids that.
NORMALIZED_KERNELSPEC = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}


def clear_notebook_outputs(path: Path) -> bool:
    """Clear tracked execution state and pin kernel metadata, returning whether it changed."""
    notebook = nbformat.read(path, as_version=4)
    changed = False

    if notebook.metadata.get("kernelspec") != NORMALIZED_KERNELSPEC:
        notebook.metadata["kernelspec"] = dict(NORMALIZED_KERNELSPEC)
        changed = True
    if notebook.metadata.pop("language_info", None) is not None:
        changed = True

    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        if cell.get("outputs") or cell.get("execution_count") is not None:
            changed = True
        cell.outputs = []
        cell.execution_count = None
    if changed:
        nbformat.write(notebook, path)
    return changed


def main(paths: list[str]) -> int:
    for name in paths:
        path = Path(name)
        if clear_notebook_outputs(path):
            print(f"Cleared outputs from {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
