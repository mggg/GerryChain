"""Sphinx configuration for the GerryChain documentation."""

import os
import sys
from importlib.metadata import version as package_version

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

# The "tangerine" palette from binary-ensemble's docs: a warm cream light mode and a warm
# near-black dark mode with an orange / cerulean (complementary) accent pair. ben-py bakes
# only the brand colors and lets its palette-switcher JS paint the rest at load; we don't
# carry the switcher, so the full palette is baked here.
html_theme_options = {
    "light_css_variables": {
        "color-background-primary": "#fbfaf2",
        "color-background-secondary": "#f1f0e6",
        "color-foreground-primary": "#140f0c",
        "color-brand-primary": "#c2410c",
        "color-brand-content": "#0077c4",
        "color-admonition-title--note": "#087fc7",
        "color-admonition-title-background--note": "rgba(8, 127, 199, 0.18)",
    },
    "dark_css_variables": {
        "color-background-primary": "#1c1917",
        "color-background-secondary": "#292524",
        "color-foreground-primary": "#fcffff",
        "color-brand-primary": "#ff750f",
        "color-brand-content": "#0097d4",
        "color-admonition-title--note": "#169bd5",
        "color-admonition-title-background--note": "rgba(22, 155, 213, 0.2)",
    },
}

# The matching code themes (also from ben-py), resolved through Sphinx's dotted-path
# support for Pygments styles.
pygments_style = "_pygments_warm.WarmLightStyle"
pygments_dark_style = "_pygments_warm.WarmDarkStyle"

html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
htmlhelp_basename = "GerryChaindoc"

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
