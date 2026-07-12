"""Execute every Python code block in the documentation.

The docs are the single source of truth: this runner discovers ``docs/**/*.md`` and
``docs/**/*.rst`` (the autodoc reference pages and the repo README are still RST), extracts
every Python code block, and executes each page's blocks in order in a shared namespace inside
a temp working directory. Tutorial notebooks are not covered here; they execute through
``make docs-refresh-notebooks`` and the CI freshness check. The runner generically stages files
from ``docs/_static`` so download-based examples can use the same filenames readers receive.

Pages can annotate a block with a marker on the line before it (blank lines allowed between).
In RST the marker is a comment, in Markdown an HTML comment:

    .. docs-test: skip -- <reason>
    .. docs-test: setup

    <!-- docs-test: skip -- <reason> -->
    <!-- docs-test: setup -->

``skip`` excludes the block from execution and requires a short reason. ``setup`` blocks are run
once, before any page, in the shared working directory (e.g. to unzip downloaded data).
"""

import os

os.environ.setdefault("MPLBACKEND", "Agg")

import re
import sys
import textwrap
from base64 import b64encode
from dataclasses import dataclass
from io import BytesIO
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from gerrychain import set_runtime_checks

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
STATIC = DOCS / "_static"

MARKERS = ("skip", "setup")

RST_BLOCK_RE = re.compile(r"^(?P<indent>[ \t]*)\.\.\s+code(?:-block)?::\s+python[ \t]*$")
RST_MARKER_RE = re.compile(
    r"^[ \t]*\.\.\s+docs-test:\s*(?P<name>[\w-]+)[ \t]*(?:--[ \t]*(?P<reason>.*\S))?[ \t]*$"
)
RST_OPTION_RE = re.compile(r"^[ \t]*:[\w-]+:")
MD_FENCE_RE = re.compile(r"^(?P<indent>[ \t]*)```python[ \t]*$")
MD_MARKER_RE = re.compile(
    r"^[ \t]*<!--\s*docs-test:\s*(?P<name>[\w-]+)[ \t]*(?:--[ \t]*(?P<reason>.*?))?\s*-->[ \t]*$"
)

# Loose pattern used by the completeness check: anything that looks like a Python code directive
# must have been extracted by the strict scanner above (or the scanner needs fixing).
RST_LOOSE_RE = re.compile(r"code(?:-block)?::\s*python", re.IGNORECASE)
MD_LOOSE_RE = re.compile(r"^[ \t]*```python", re.MULTILINE)


@dataclass
class Block:
    page: Path
    lineno: int  # 1-based line of the block's first code line, for tracebacks
    source: str
    marker: str | None = None
    reason: str | None = None


def _check_marker(name: str, reason: str | None, page: Path, lineno: int) -> None:
    if name not in MARKERS:
        raise ValueError(f"{page}:{lineno}: unknown docs-test marker {name!r}")
    if name == "skip" and not reason:
        raise ValueError(f"{page}:{lineno}: docs-test: skip requires a reason ('-- <reason>')")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def extract_rst_blocks(text: str, page: Path) -> list[Block]:
    """Extract ``.. code-block:: python`` / ``.. code:: python`` bodies, dedented."""
    lines = text.split("\n")
    blocks: list[Block] = []
    marker: tuple[str, str | None, int] | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = RST_MARKER_RE.match(line)
        if m:
            _check_marker(m["name"], m["reason"], page, i + 1)
            marker = (m["name"], m["reason"], i + 1)
            i += 1
            continue
        d = RST_BLOCK_RE.match(line)
        if d is None:
            if line.strip():
                marker = None  # markers survive only blank lines
            i += 1
            continue
        indent = len(d["indent"])
        i += 1
        # Consume option lines (":linenos:" etc.) attached directly to the directive.
        while i < len(lines) and lines[i].strip() and _indent(lines[i]) > indent:
            if not RST_OPTION_RE.match(lines[i]):
                break
            i += 1
        # Body: everything more indented than the directive, up to the indentation boundary.
        body: list[str] = []
        first_code_line = None
        while i < len(lines):
            cur = lines[i]
            if cur.strip():
                if _indent(cur) <= indent:
                    break
                if first_code_line is None:
                    first_code_line = i + 1
            if first_code_line is not None:
                body.append(cur)
            i += 1
        while body and not body[-1].strip():
            body.pop()
        source = textwrap.dedent("\n".join(body))
        blocks.append(
            Block(
                page=page,
                lineno=first_code_line or i,
                source=source,
                marker=marker[0] if marker else None,
                reason=marker[1] if marker else None,
            )
        )
        marker = None
    return blocks


def extract_md_blocks(text: str, page: Path) -> list[Block]:
    """Extract ```python fenced blocks from (MyST) Markdown, dedented."""
    lines = text.split("\n")
    blocks: list[Block] = []
    marker: tuple[str, str | None] | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = MD_MARKER_RE.match(line)
        if m:
            _check_marker(m["name"], m["reason"], page, i + 1)
            marker = (m["name"], m["reason"])
            i += 1
            continue
        f = MD_FENCE_RE.match(line)
        if f is None:
            if line.strip():
                marker = None
            i += 1
            continue
        indent = f["indent"]
        i += 1
        first_code_line = i + 1
        body = []
        while i < len(lines) and lines[i].strip() != "```":
            body.append(lines[i].removeprefix(indent))
            i += 1
        i += 1  # closing fence
        blocks.append(
            Block(
                page=page,
                lineno=first_code_line,
                source="\n".join(body),
                marker=marker[0] if marker else None,
                reason=marker[1] if marker else None,
            )
        )
        marker = None
    return blocks


def extract_blocks(page: Path) -> list[Block]:
    text = page.read_text(encoding="utf-8")
    if page.suffix == ".md":
        return extract_md_blocks(text, page)
    return extract_rst_blocks(text, page)


def discover_pages() -> list[Path]:
    pages = [
        p for pattern in ("*.rst", "*.md") for p in DOCS.rglob(pattern) if "_build" not in p.parts
    ]
    pages.append(REPO / "README.rst")
    return sorted(pages)


PAGES = discover_pages()
ALL_BLOCKS = {page: extract_blocks(page) for page in PAGES}
EXEC_PAGES = [page for page, blocks in ALL_BLOCKS.items() if blocks]


def _page_id(page: Path) -> str:
    return str(page.relative_to(REPO))


def _run_block(block: Block, namespace: dict) -> None:
    # Pad the source so tracebacks and SyntaxErrors point at the real line in the docs page.
    padded = "\n" * (block.lineno - 1) + block.source
    exec(compile(padded, str(block.page), "exec"), namespace)


@pytest.fixture(scope="session")
def docs_cwd(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Shared working directory with the documented downloads staged, setup blocks applied."""
    cwd = tmp_path_factory.mktemp("docs-snippets")
    for source in STATIC.iterdir():
        if source.is_file():
            (cwd / source.name).symlink_to(source)
    old = os.getcwd()
    os.chdir(cwd)
    try:
        namespace: dict = {}
        for page in PAGES:
            for block in ALL_BLOCKS[page]:
                if block.marker == "setup":
                    _run_block(block, namespace)
    finally:
        os.chdir(old)
    return cwd


@pytest.mark.docs
@pytest.mark.parametrize("page", EXEC_PAGES, ids=_page_id)
def test_page_snippets(page: Path, docs_cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Docs snippets run as a user would, without the suite-wide runtime integrity checks
    # (the conftest fixture re-enables its previous state afterwards).
    set_runtime_checks(False)
    monkeypatch.chdir(docs_cwd)
    namespace: dict = {}
    try:
        for block in ALL_BLOCKS[page]:
            if block.marker in MARKERS:
                continue
            _run_block(block, namespace)
    finally:
        if "matplotlib.pyplot" in sys.modules:
            sys.modules["matplotlib.pyplot"].close("all")


@pytest.mark.parametrize("page", PAGES, ids=_page_id)
def test_every_python_block_is_extracted(page: Path) -> None:
    """Anything that looks like a Python block must be extracted (or the scanner fixed)."""
    text = page.read_text(encoding="utf-8")
    loose_re = MD_LOOSE_RE if page.suffix == ".md" else RST_LOOSE_RE
    assert len(loose_re.findall(text)) == len(ALL_BLOCKS[page])


# ---------------------------------------------------------------------------
# Extractor unit tests
# ---------------------------------------------------------------------------

FAKE = Path("fake.rst")


def rst_blocks(text: str) -> list[Block]:
    return extract_rst_blocks(textwrap.dedent(text), FAKE)


class TestRstExtractor:
    def test_top_level_block(self) -> None:
        blocks = rst_blocks(
            """\
            Some prose.

            .. code-block:: python

                x = 1
                y = x + 1

            More prose.
            """
        )
        assert len(blocks) == 1
        assert blocks[0].source == "x = 1\ny = x + 1"
        assert blocks[0].lineno == 5

    def test_code_directive_variant_and_trailing_whitespace(self) -> None:
        blocks = rst_blocks(".. code:: python  \n\n    x = 1\n")
        assert len(blocks) == 1
        assert blocks[0].source == "x = 1"

    def test_nested_block_terminates_at_directive_indent(self) -> None:
        blocks = rst_blocks(
            """\
            .. admonition:: Note

                Some explanation.

                .. code-block:: python

                    x = 1

                This prose is back at the admonition level, not code.
            """
        )
        assert len(blocks) == 1
        assert blocks[0].source == "x = 1"

    def test_adjacent_blocks(self) -> None:
        blocks = rst_blocks(
            """\
            .. code-block:: python

                x = 1

            .. code-block:: python

                y = 2
            """
        )
        assert [b.source for b in blocks] == ["x = 1", "y = 2"]

    def test_interior_blank_lines_preserved(self) -> None:
        blocks = rst_blocks(".. code-block:: python\n\n    x = 1\n\n    y = 2\n")
        assert blocks[0].source == "x = 1\n\ny = 2"

    def test_option_lines_are_not_code(self) -> None:
        blocks = rst_blocks(
            """\
            .. code-block:: python
                :linenos:

                x = 1
            """
        )
        assert blocks[0].source == "x = 1"

    def test_skip_marker_with_reason(self) -> None:
        blocks = rst_blocks(
            """\
            .. docs-test: skip -- needs network access

            .. code-block:: python

                x = 1
            """
        )
        assert blocks[0].marker == "skip"
        assert blocks[0].reason == "needs network access"

    def test_skip_without_reason_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="requires a reason"):
            rst_blocks(".. docs-test: skip\n\n.. code-block:: python\n\n    x = 1\n")

    def test_unknown_marker_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="unknown docs-test marker"):
            rst_blocks(".. docs-test: sikp -- oops\n\n.. code-block:: python\n\n    x = 1\n")

    def test_setup_marker(self) -> None:
        blocks = rst_blocks(".. docs-test: setup\n\n.. code-block:: python\n\n    x = 1\n")
        assert blocks[0].marker == "setup"

    def test_marker_does_not_survive_intervening_prose(self) -> None:
        blocks = rst_blocks(
            """\
            .. docs-test: skip -- for the next block

            Some prose in between.

            .. code-block:: python

                x = 1
            """
        )
        assert blocks[0].marker is None

    def test_non_python_blocks_ignored(self) -> None:
        assert rst_blocks(".. code-block:: console\n\n    $ ls\n") == []

    def test_extracted_source_is_executable(self) -> None:
        blocks = rst_blocks(
            """\
            .. code-block:: python

                def f():
                    return 41

                x = f() + 1
            """
        )
        namespace: dict = {}
        _run_block(blocks[0], namespace)
        assert namespace["x"] == 42


class TestMdExtractor:
    def test_fence_with_marker(self) -> None:
        text = textwrap.dedent(
            """\
            Some prose.

            <!-- docs-test: skip -- interactive only -->

            ```python
            x = 1
            ```
            """
        )
        blocks = extract_md_blocks(text, Path("fake.md"))
        assert len(blocks) == 1
        assert blocks[0].source == "x = 1"
        assert blocks[0].marker == "skip"
        assert blocks[0].reason == "interactive only"

    def test_plain_fence_and_non_python_ignored(self) -> None:
        text = "```python\nx = 1\ny = 2\n```\n\n```console\n$ ls\n```\n"
        blocks = extract_md_blocks(text, Path("fake.md"))
        assert len(blocks) == 1
        assert blocks[0].source == "x = 1\ny = 2"
        assert blocks[0].marker is None


@pytest.mark.docs
class TestNotebookImageComparison:
    @staticmethod
    def refresh_module():
        spec = spec_from_file_location("refresh_notebooks", DOCS / "_refresh_notebooks.py")
        assert spec is not None and spec.loader is not None
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def image_payload(color: str, changed_pixel: bool = False) -> str:
        from PIL import Image

        image = Image.new("RGB", (100, 100), color)
        if changed_pixel:
            image.putpixel((0, 0), (0, 0, 0))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return b64encode(buffer.getvalue()).decode()

    def test_material_image_changes_are_detected(self) -> None:
        refresh = self.refresh_module()
        assert not refresh._images_match(self.image_payload("white"), self.image_payload("black"))
        assert not refresh._images_match(self.image_payload("white"), "corrupt")

    def test_tiny_image_changes_are_tolerated(self) -> None:
        refresh = self.refresh_module()
        assert refresh._images_match(
            self.image_payload("white"), self.image_payload("white", changed_pixel=True)
        )
