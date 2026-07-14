"""Execute tutorial notebooks into MyST-NB's ignored output cache.

Usage:
    python docs/_refresh_notebooks.py [NOTEBOOK ...]

With no arguments every notebook under ``docs/user/`` is checked. Notebooks missing from the cache
run in a fresh kernel inside a temporary working directory seeded with the committed sample data,
so the guides' verbatim ``./PA_VTDs.json``-style paths resolve. Executed notebooks are stored in
MyST-NB's cache under ``docs/_build/``; committed notebooks remain output-free and reviewable.
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

import nbformat
from jupyter_cache import get_cache
from jupyter_cache.base import CacheBundleIn, JupyterCacheAbstract
from nbclient import NotebookClient

DOCS = Path(__file__).resolve().parent
TUTORIALS = DOCS / "user"
CACHE = DOCS / "_build" / ".jupyter_cache"
# Committed sample data the guides load with bare relative paths, mirroring the
# docs_cwd fixture in tests/test_docs_snippets.py.
DATA_FILES = ("PA_VTDs.json", "05_bg_census_consolidated.json", "MN.zip")


def normalize(nb: nbformat.NotebookNode) -> None:
    """Strip metadata and output noise that varies between runs or machines."""
    nb.metadata.pop("language_info", None)
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    for cell in nb.cells:
        cell.metadata.pop("execution", None)
        merged: list[nbformat.NotebookNode] = []
        for output in cell.get("outputs", []):
            output.get("metadata", {}).pop("filenames", None)
            # Object reprs embed the allocation address, which is fresh every run.
            data = output.get("data", {})
            if "text/plain" in data:
                data["text/plain"] = re.sub(r"0x[0-9a-f]+", "0x...", data["text/plain"])
            if "text" in output:
                output["text"] = re.sub(r"0x[0-9a-f]+", "0x...", output["text"])
            # Kernel flush timing splits identical stdout into a varying number of
            # stream outputs; coalesce consecutive same-stream chunks.
            if (
                output.get("output_type") == "stream"
                and merged
                and merged[-1].get("output_type") == "stream"
                and merged[-1].get("name") == output.get("name")
            ):
                merged[-1]["text"] += output["text"]
            else:
                merged.append(output)
        if "outputs" in cell:
            cell["outputs"] = merged


def execute(path: Path) -> nbformat.NotebookNode:
    nb = nbformat.read(path, as_version=4)
    nb.metadata.pop("widgets", None)
    with tempfile.TemporaryDirectory() as cwd:
        for name in DATA_FILES:
            (Path(cwd) / name).symlink_to(DOCS / "_static" / name)
        client = NotebookClient(
            nb,
            timeout=600,
            kernel_name="python3",
            resources={"metadata": {"path": cwd}},
        )
        client.execute()
    normalize(nb)
    return nb


def notebook_is_cached(path: Path, cache: JupyterCacheAbstract) -> bool:
    """Return whether the cache contains outputs for the notebook's current source."""
    try:
        cache.match_cache_notebook(nbformat.read(path, as_version=4))
    except KeyError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "notebooks",
        nargs="*",
        type=Path,
        help="notebooks to cache (default: every notebook under docs/user/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="execute notebooks even when matching cached outputs exist",
    )
    args = parser.parse_args()
    notebooks = args.notebooks or sorted(TUTORIALS.glob("*.ipynb"))
    if not notebooks:
        print("No notebooks found.")
        return 0
    cache = get_cache(str(CACHE))
    for path in notebooks:
        path = Path(path)
        if not args.force and notebook_is_cached(path, cache):
            print(f"Using cached {path}")
            continue
        print(f"Caching {path} ...", flush=True)
        cache.cache_notebook_bundle(
            CacheBundleIn(execute(path), str(path.resolve())),
            check_validity=False,
            overwrite=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
