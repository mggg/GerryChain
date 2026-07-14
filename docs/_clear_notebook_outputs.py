"""Remove generated outputs and execution counts from notebooks."""

import sys
from pathlib import Path

import nbformat


def clear_notebook_outputs(path: Path) -> bool:
    """Clear tracked execution state, returning whether the notebook changed."""
    notebook = nbformat.read(path, as_version=4)
    changed = False
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
