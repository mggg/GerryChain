"""Re-execute tutorial notebooks in place and normalize volatile metadata.

Usage:
    python docs/_refresh_notebooks.py [--check] [NOTEBOOK ...]

With no arguments every notebook under ``docs/user/`` is refreshed. Each notebook executes
in a fresh kernel inside a temporary working directory seeded with the committed sample
data (so the guides' verbatim ``./PA_VTDs.json``-style paths resolve), then volatile
metadata (per-cell execution timing, kernel/language version details) is stripped so that
re-running the refresh with an unchanged library produces a byte-identical file.

``--check`` executes each notebook and compares the result against the committed file instead of
writing, failing if they differ; CI uses this to prove the committed outputs match what the current
code produces. Images are decoded and compared perceptually so renderer noise is tolerated without
letting materially stale or corrupt plots pass.
"""

import argparse
import base64
import re
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from PIL import Image, ImageChops, ImageStat, UnidentifiedImageError

DOCS = Path(__file__).resolve().parent
TUTORIALS = DOCS / "user"
# Committed sample data the guides load with bare relative paths, mirroring the
# docs_cwd fixture in tests/test_docs_snippets.py.
DATA_FILES = ("PA_VTDs.json", "05_bg_census_consolidated.json", "MN.zip")
IMAGE_SIZE = (64, 64)
IMAGE_MEAN_DIFFERENCE = 3.0
DATA_IMAGE_RE = re.compile(r"data:image/[^;]+;base64,((?:[A-Za-z0-9+/=]|\\\s*)+)")
ANIMATION_ID_RE = re.compile(r"(?<=[A-Za-z_])[0-9a-f]{32}\b")


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


def _without_images(nb: nbformat.NotebookNode) -> tuple[dict, list[str]]:
    """Return notebook structure without image payloads, plus those payloads."""
    stripped = nbformat.from_dict(nb)
    images = []
    for cell in stripped.cells:
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            for mime in list(data):
                if mime.startswith("image/"):
                    images.append(data[mime])
                    data[mime] = "<image>"
            html = data.get("text/html")
            if html:
                def replace_image(match: re.Match[str]) -> str:
                    images.append(re.sub(r"\\\s*", "", match.group(1)))
                    return "data:image/png;base64,<image>"

                html = DATA_IMAGE_RE.sub(replace_image, html)
                data["text/html"] = ANIMATION_ID_RE.sub("<id>", html)
    return dict(stripped), images


def _decode_image(payload: str) -> Image.Image | None:
    try:
        return Image.open(BytesIO(base64.b64decode(payload))).convert("RGB")
    except (OSError, UnidentifiedImageError, ValueError):
        return None


def _images_match(left: str, right: str) -> bool:
    left_image = _decode_image(left)
    right_image = _decode_image(right)
    if left_image is None or right_image is None or left_image.size != right_image.size:
        return False

    # ponytail: a 64px perceptual comparison tolerates font-renderer noise; use a fixed docs
    # container if pixel-exact plots ever become contractual.
    left_image.thumbnail(IMAGE_SIZE)
    right_image.thumbnail(IMAGE_SIZE)
    difference = ImageChops.difference(left_image, right_image)
    return sum(ImageStat.Stat(difference).mean) / 3 <= IMAGE_MEAN_DIFFERENCE


def notebooks_match(left: nbformat.NotebookNode, right: nbformat.NotebookNode) -> bool:
    left_notebook, left_images = _without_images(left)
    right_notebook, right_images = _without_images(right)
    return (
        left_notebook == right_notebook
        and len(left_images) == len(right_images)
        and all(
            _images_match(left_image, right_image)
            for left_image, right_image in zip(left_images, right_images, strict=True)
        )
    )


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="execute and compare against the committed outputs instead of writing",
    )
    parser.add_argument(
        "notebooks",
        nargs="*",
        type=Path,
        help="notebooks to refresh (default: every notebook under docs/user/)",
    )
    args = parser.parse_args()
    notebooks = args.notebooks or sorted(TUTORIALS.glob("*.ipynb"))
    if not notebooks:
        print("No notebooks found.")
        return 0
    stale = []
    for path in notebooks:
        path = Path(path)
        if args.check:
            print(f"Checking {path} ...", flush=True)
            committed = nbformat.read(path, as_version=4)
            if not notebooks_match(execute(path), committed):
                stale.append(path)
        else:
            print(f"Refreshing {path} ...", flush=True)
            nbformat.write(execute(path), path)
    if stale:
        names = ", ".join(str(path) for path in stale)
        print(
            f"STALE committed outputs: {names}\n"
            "Run `make docs-refresh-notebooks` and commit the result.",
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
