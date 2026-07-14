"""Sphinx configuration for the GerryChain documentation."""

import json
import os
import sys
from importlib.metadata import version as package_version

from sphinx.application import Sphinx

# Make docs/_pygments_warm.py importable for the dotted pygments_style paths below.
sys.path.insert(0, os.path.dirname(__file__))

# -- Project information -----------------------------------------------------

project = "GerryChain"
copyright = "2018-2026, Metric Geometry and Gerrymandering Group"
author = "Metric Geometry and Gerrymandering Group"

release = package_version("gerrychain")
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_design",
    "myst_nb",  # includes myst_parser
]

myst_enable_extensions = [
    "colon_fence",  # ::: fences for the sphinx-design cards on the landing page
    "deflist",  # definition lists inside {glossary} directives
    "dollarmath",
]
myst_heading_anchors = 3

# Tutorial notebooks are committed with their outputs. The default "off" renders those
# outputs directly (ReadTheDocs and the CI build); developers can set
# NB_EXECUTION_MODE=cache for an execution-checking preview. Keeping committed outputs
# fresh is enforced separately by `make docs-check-notebooks` in CI.
nb_execution_mode = os.environ.get("NB_EXECUTION_MODE", "off")
nb_execution_timeout = 600
nb_execution_raise_on_error = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "networkx": ("https://networkx.org/documentation/stable/", None),
    "rustworkx": ("https://www.rustworkx.org/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
}

templates_path = ["_templates"]
# jupyter_execute is myst-nb's notebook-output mirror, not a documentation source.
exclude_patterns = ["_build", "jupyter_execute", "Thumbs.db", ".DS_Store"]
language = "en"
master_doc = "index"

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"
html_title = "GerryChain"

# -- Color palettes -----------------------------------------------------------
#
# Palette registry + live switcher ported from binary-ensemble's docs (ben-py). Each
# entry maps a mode ("light"/"dark") to a dict of Furo CSS variables. Every palette
# carries the same keys, so a browser-side switch repaints every variable and reverts
# cleanly. "tangerine" is the current shipped palette (ben-py's orange), kept for
# comparison; "blush-blue" is the chosen palette: rose paper with ocean-blue
# headings/sidebar (#00688a, the #00749A seed deepened one step so it clears 4.5:1 on
# secondary surfaces too), MGGG-maroon links (#800001), and blue badges. Accents clear
# WCAG 4.5:1 on both surfaces in both modes.
#
# A palette's "light_pygments" / "dark_pygments" name the Pygments styles used for code
# blocks in each mode while it is active (the code dropdown's "Auto" entry); each must
# appear in CODE_THEMES or CUSTOM_STYLES below.
#
# Pick the palette with the DOCS_PALETTE env var, and set DOCS_SWITCHER=1 to render the
# in-browser dropdown for live side-by-side comparison:
#
#     DOCS_SWITCHER=1 DOCS_PALETTE=cream make docs-serve


# (background, secondary background, foreground, brand-primary/content, badge, visited badge)
def _mode(
    bg: str, bg2: str, fg: str, primary: str, content: str, badge: str, badge_visited: str
) -> dict[str, str]:
    return {
        "color-background-primary": bg,
        "color-background-secondary": bg2,
        "color-foreground-primary": fg,
        "color-brand-primary": primary,
        "color-brand-content": content,
        "color-download-badge-background": badge,
        "color-download-badge-background-visited": badge_visited,
    }


PALETTES = {
    # ben-py's warm cream / near-black with an orange + cerulean accent pair (current).
    "tangerine": {
        "light_pygments": "warm-light",
        "dark_pygments": "warm-dark",
        "light": _mode("#fbfaf2", "#f1f0e6", "#140f0c", "#c2410c", "#0077c4", "#c2410c", "#7c2d12"),
        "dark": _mode("#1c1917", "#292524", "#fcffff", "#ff750f", "#0097d4", "#9a3412", "#6b250c"),
    },
    # blush, roles swapped: ocean-blue headings/sidebar, maroon links, blue badges.
    "blush-blue": {
        "light_pygments": "harbor-blush-light",
        "dark_pygments": "harbor-blush-dark",
        "light": _mode("#f4ebe7", "#ecdbd6", "#231412", "#00688a", "#800001", "#00688a", "#00445c"),
        "dark": _mode("#1d1618", "#2b2024", "#f4ebee", "#3cb4dc", "#ec8383", "#0a6a8c", "#06485f"),
    },
}
ACTIVE_PALETTE = os.environ.get("DOCS_PALETTE", "blush-blue")
_palette = PALETTES[ACTIVE_PALETTE]

# Whether to render the in-browser palette dropdown. Off by default so the published site
# ships locked to the active palette; set DOCS_SWITCHER=1 while developing to compare.
SHOW_SWITCHER = os.environ.get("DOCS_SWITCHER", "").lower() not in ("", "0", "false", "no")

# Env vars and plain module globals aren't Sphinx config values, so flipping
# DOCS_SWITCHER (or tweaking a non-active palette, which is only baked into each page's
# injected JS) would leave a cached build untouched. Mirroring them into html_context
# makes them tracked config values, forcing an HTML rebuild when any of them change.
html_context = {
    "docs_show_switcher": SHOW_SWITCHER,
    "docs_palettes": PALETTES,
    "docs_active_palette": ACTIVE_PALETTE,
}

# Bake the full active palette (every palette carries the same keys, so live switching
# still repaints everything and reverts cleanly; baking keeps a no-JS fallback). The
# admonition tints and visited-badge text are palette-agnostic and shared by every
# candidate, so they live here rather than in the registry.
html_theme_options = {
    "light_css_variables": {
        **_palette["light"],
        "color-download-badge-visited": "#d8b4fe",
        "color-admonition-title--note": "#087fc7",
        "color-admonition-title-background--note": "rgba(8, 127, 199, 0.18)",
    },
    "dark_css_variables": {
        **_palette["dark"],
        "color-download-badge-visited": "#d8b4fe",
        "color-admonition-title--note": "#169bd5",
        "color-admonition-title-background--note": "rgba(22, 155, 213, 0.2)",
    },
}

# The globally baked code themes, resolved through Sphinx's dotted-path support for
# Pygments styles. These are the no-JS fallback; with JS, each palette's
# light_pygments/dark_pygments defaults win (see CODE_THEMES below).
pygments_style = "_pygments_warm.HarborBlushLightStyle"
pygments_dark_style = "_pygments_warm.HarborBlushDarkStyle"

html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
htmlhelp_basename = "GerryChaindoc"

# -- Swappable code (Pygments) themes ------------------------------------------
#
# From ben-py: Furo bakes one light + one dark Pygments theme into pygments.css, so to
# make code themes swappable (per palette and live in the browser) every style below is
# pre-rendered into one generated stylesheet and keyed off a <body> attribute the
# switcher sets: data-code-theme for an explicit dropdown pick (applies in both modes),
# data-code-auto / data-code-auto-light for the active palette's per-mode defaults.
#
# CODE_THEMES is the dropdown menu, grouped into <optgroup>s; any valid Pygments style
# name works (`python -m pygments -L styles`). The garnet pair is the red/blue candidate
# matching the round-2 palettes; the warm pair matches tangerine; the rest are stock
# themes for comparison.
CODE_THEMES = {
    "Dark": [
        "harbor-blush-dark",
        "warm-dark",
        "github-dark",
        "gruvbox-dark",
        "one-dark",
        "dracula",
        "nord",
        "monokai",
    ],
    "Light": [
        "harbor-blush-light",
        "warm-light",
        "github-light",
        "gruvbox-light",
        "solarized-light",
        "friendly",
        "xcode",
    ],
}

# Custom (non-builtin) styles, keyed by the name used in CODE_THEMES and the palettes'
# light_pygments/dark_pygments defaults. HtmlFormatter accepts a Style class directly.
import _pygments_warm  # noqa: E402  (needs the sys.path tweak at the top)

CUSTOM_STYLES = {
    "warm-light": _pygments_warm.WarmLightStyle,
    "warm-dark": _pygments_warm.WarmDarkStyle,
    "harbor-blush-light": _pygments_warm.HarborBlushLightStyle,
    "harbor-blush-dark": _pygments_warm.HarborBlushDarkStyle,
}

# Track the menu for cache invalidation, same reason as the palette mirror above.
html_context["docs_code_themes"] = CODE_THEMES


# Lock the blush-blue code surfaces to its sidebar surface: both are the same 60/40
# canvas/secondary mix (custom.css computes the sidebar's in the browser with color-mix;
# this bakes the identical value into the style class before the themes are rendered
# below).
def _mix60(a: str, b: str) -> str:
    return "#" + "".join(
        f"{round(0.6 * int(a[i : i + 2], 16) + 0.4 * int(b[i : i + 2], 16)):02x}" for i in (1, 3, 5)
    )


def _bind_code_surface(style: type, palette: str, mode: str) -> None:
    m = PALETTES[palette][mode]
    style.background_color = _mix60(m["color-background-primary"], m["color-background-secondary"])


_bind_code_surface(_pygments_warm.HarborBlushLightStyle, "blush-blue", "light")
_bind_code_surface(_pygments_warm.HarborBlushDarkStyle, "blush-blue", "dark")


def _pygments_theme_css() -> str:
    from pygments.formatters import HtmlFormatter

    menu = [s for group in CODE_THEMES.values() for s in group]
    dark_defaults = [p["dark_pygments"] for p in PALETTES.values() if p.get("dark_pygments")]
    light_defaults = [p["light_pygments"] for p in PALETTES.values() if p.get("light_pygments")]

    def make_formatter(style: str) -> HtmlFormatter:
        return HtmlFormatter(style=CUSTOM_STYLES.get(style, style))

    def rules(formatter: HtmlFormatter, prefix: str) -> str:
        # get_style_defs prefixes the token rules (and the `.highlight {background}` line)
        # with `prefix`; keep only those, dropping Pygments' un-prefixed globals
        # (pre{}, td.linenos{}) so nothing leaks outside code blocks.
        return "\n".join(
            line
            for line in formatter.get_style_defs(f"{prefix} .highlight").splitlines()
            if line.startswith(f"{prefix} .highlight")
        )

    blocks = []
    # Explicit picks (and any palette default, so it resolves even if absent from the
    # menu) apply in any mode via the order-independent `html body` prefix.
    for style in dict.fromkeys(menu + dark_defaults + light_defaults):
        blocks.append(rules(make_formatter(style), f'html body[data-code-theme="{style}"]'))
    # "Auto" applies a palette's dark/light default, each scoped to its own mode so the
    # other mode keeps the global Pygments style. The auto-mode (`prefers-color-scheme`)
    # variants mirror Furo's `:not([data-theme=…])` selectors for system readers.
    for style in dict.fromkeys(dark_defaults):
        fmt = make_formatter(style)
        blocks.append(rules(fmt, f'body[data-theme="dark"][data-code-auto="{style}"]'))
        auto = rules(fmt, f'body:not([data-theme="light"])[data-code-auto="{style}"]')
        blocks.append("@media (prefers-color-scheme: dark){\n" + auto + "\n}")
    for style in dict.fromkeys(light_defaults):
        fmt = make_formatter(style)
        blocks.append(rules(fmt, f'body[data-theme="light"][data-code-auto-light="{style}"]'))
        auto = rules(fmt, f'body:not([data-theme="dark"])[data-code-auto-light="{style}"]')
        blocks.append("@media (prefers-color-scheme: light){\n" + auto + "\n}")
    return "\n".join(blocks)


# The rendered themes are large, so write them to one linked stylesheet (the browser
# caches it once) instead of inlining them into every page. The file lives in a
# build-only, git-ignored "_generated" static dir that html_static_path picks up.
# Rewrite it only when the content actually changes: conf.py re-runs on every build, and
# docs-serve (sphinx-autobuild) watches docs/, so an unconditional write would retrigger
# the watcher in an endless rebuild loop that also keeps reloading the browser.
_generated = os.path.join(os.path.dirname(__file__), "_generated", "css")
os.makedirs(_generated, exist_ok=True)
_themes_path = os.path.join(_generated, "pygments-themes.css")
_themes_css = _pygments_theme_css()
try:
    with open(_themes_path, encoding="utf-8") as _f:
        _themes_current = _f.read()
except OSError:
    _themes_current = None
if _themes_current != _themes_css:
    with open(_themes_path, "w", encoding="utf-8") as _f:
        _f.write(_themes_css)
html_static_path.append("_generated")
html_css_files.append("css/pygments-themes.css")

# -- Autodoc / Napoleon ------------------------------------------------------

# Append the __init__ docstring to the class docstring.
autoclass_content = "both"
add_module_names = True
autodoc_inherit_docstrings = False

# Docstrings are Google style throughout the codebase.
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# -- linkcheck ---------------------------------------------------------------

# Hosts with narrow, observed problems only; keep a reason beside each entry.
linkcheck_ignore = []

# GitHub renders README heading anchors client-side (e.g. mggg/maup#readme), so
# linkcheck cannot see them in the served HTML.
linkcheck_anchors_ignore_for_url = [r"https://github\.com/.*"]

# -- In-browser palette switcher ----------------------------------------------


# Expose the palette and code-theme registries to the page (single source of truth) and
# add the switcher script (from ben-py). The script paints the active palette and its
# default code themes on load and, when DOCS_SWITCHER is set, renders the 🎨 palette and
# </> code-theme dropdowns; choices recolor the live site and persist in localStorage.
# Delete this setup() and js/palette-switcher.js to remove it.
def setup(app: Sphinx) -> None:
    app.add_js_file(
        None,
        body=(
            f"window.DOCS_PALETTES = {json.dumps(PALETTES)};\n"
            f"window.DOCS_PALETTE_DEFAULT = {json.dumps(ACTIVE_PALETTE)};\n"
            f"window.DOCS_CODE_THEMES = {json.dumps(CODE_THEMES)};\n"
            f"window.DOCS_SHOW_SWITCHER = {json.dumps(SHOW_SWITCHER)};"
        ),
    )
    app.add_js_file("js/palette-switcher.js")
