"""Custom Pygments styles for the docs.

``WarmLightStyle`` / ``WarmDarkStyle`` are ported from binary-ensemble's warm "tangerine"
palette: tokens drawn from that brand accent family (orange and amber warms against cerulean
and teal cools) rather than a stock theme's unrelated hues.

``HarborBlushLightStyle`` / ``HarborBlushDarkStyle`` are the pair for the "blush-blue"
palette, mirroring its page hierarchy: ocean-blue keywords (#0099cc in dark, the logo cyan)
with MGGG-maroon functions and classes, strings in a deep green, numbers and True/False/None
in the logo-indigo and amber families, exceptions in vermilion, on rose surfaces that
conf.py binds to the palette's sidebar mix at build time.

Light-mode tokens clear ~4.5:1 contrast on their background and dark-mode tokens ~5:1+
(except the dark maroon, a deliberate ~3.8:1 trade for its depth), so the light/dark pairs
feel consistent.

conf.py points ``pygments_style`` / ``pygments_dark_style`` here via Sphinx's dotted-path
support ("module.ClassName"), and registers all four in its CODE_THEMES menu.
"""

from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Token,
)


class WarmLightStyle(Style):
    name = "warm-light"
    background_color = "#f6f1e7"
    highlight_color = "#e7dcc4"
    styles = {
        Token: "#20180f",
        Comment: "italic #685c4b",
        Comment.Preproc: "noitalic #c2410c",
        Keyword: "bold #c2410c",
        Keyword.Type: "nobold #623c00",
        Keyword.Constant: "nobold #b8336a",
        Operator: "#6a4a2a",
        Operator.Word: "bold #c2410c",
        Name.Builtin: "bold #08527d",
        Name.Function: "bold #08527d",
        Name.Class: "bold #0a5a86",
        Name.Namespace: "bold #0a5a86",
        Name.Exception: "bold #d10a46",
        Name.Variable: "#20180f",
        Name.Constant: "#623c00",
        Name.Decorator: "#c2410c",
        Name.Attribute: "#0a5a86",
        Name.Tag: "bold #0a6d3f",
        String: "bold #0a6d3f",
        String.Doc: "italic #685c4b",
        String.Escape: "bold #c2410c",
        Number: "bold #861657",
        Generic.Heading: "bold #20180f",
        Generic.Subheading: "bold #0a5a86",
        Generic.Deleted: "#b3261e",
        Generic.Inserted: "#0a6d3f",
        Generic.Error: "#b3261e",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Generic.Prompt: "bold #685c4b",
        Error: "border:#b3261e",
    }


class HarborBlushLightStyle(Style):
    name = "harbor-blush-light"
    # Static fallback; conf.py rebinds this to the palette's sidebar mix at build time.
    background_color = "#efe4df"
    highlight_color = "#e4d1c9"
    styles = {
        Token: "#1f1a12",
        Comment: "italic #6a6052",
        Comment.Preproc: "noitalic #045e7e",
        Keyword: "bold #045e7e",
        Keyword.Type: "nobold #5f4322",
        Keyword.Constant: "bold #9c5000",
        Operator: "#59503e",
        Operator.Word: "bold #045e7e",
        Name.Builtin: "bold #970301",
        Name.Function: "bold #970301",
        Name.Class: "bold #970301",
        Name.Namespace: "bold #970301",
        Name.Exception: "bold #a13508",
        Name.Variable: "#1f1a12",
        Name.Constant: "#5f4322",
        Name.Decorator: "#970301",
        Name.Attribute: "#970301",
        Name.Tag: "bold #136c3d",
        String: "bold #136c3d",
        String.Doc: "italic #6a6052",
        String.Escape: "bold #045e7e",
        Number: "bold #504a88",
        Generic.Heading: "bold #1f1a12",
        Generic.Subheading: "bold #045e7e",
        Generic.Deleted: "#a13508",
        Generic.Inserted: "#136c3d",
        Generic.Error: "#a13508",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Generic.Prompt: "bold #6a6052",
        Error: "border:#a13508",
    }


class HarborBlushDarkStyle(Style):
    name = "harbor-blush-dark"
    # Static fallback; conf.py rebinds this to the palette's sidebar mix at build time.
    background_color = "#221a1c"
    highlight_color = "#302427"
    line_number_color = "inherit"
    line_number_background_color = "transparent"
    styles = {
        Token: "#f0eeea",
        Comment: "italic #9d9284",
        Comment.Preproc: "noitalic #0099cc",
        Keyword: "bold #0099cc",
        Keyword.Type: "nobold #c68e35",
        Keyword.Constant: "bold #e08c26",
        Operator: "#bfb5a6",
        Operator.Word: "bold #0099cc",
        Name.Builtin: "bold #cc4b4b",
        Name.Function: "bold #cc4b4b",
        Name.Class: "bold #cc4b4b",
        Name.Namespace: "bold #cc4b4b",
        Name.Exception: "bold #e86d2e",
        Name.Variable: "#f0eeea",
        Name.Constant: "#c68e35",
        Name.Decorator: "#cc4b4b",
        Name.Attribute: "#cc4b4b",
        Name.Tag: "bold #3fa868",
        String: "bold #3fa868",
        String.Doc: "italic #9d9284",
        String.Escape: "bold #0099cc",
        Number: "bold #8d87d0",
        Generic.Heading: "bold #f0eeea",
        Generic.Subheading: "bold #0099cc",
        Generic.Deleted: "#e86d2e",
        Generic.Inserted: "#3fa868",
        Generic.Error: "#e86d2e",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Generic.Prompt: "bold #9d9284",
        Error: "border:#e86d2e",
    }


class WarmDarkStyle(Style):
    name = "warm-dark"
    background_color = "#292524"
    highlight_color = "#2a2218"
    line_number_color = "inherit"
    line_number_background_color = "transparent"
    styles = {
        Token: "#f4efe6",
        Comment: "italic #9a8f7c",
        Comment.Preproc: "noitalic #ff750f",
        Keyword: "bold #ff750f",
        Keyword.Type: "nobold #d8a657",
        Keyword.Constant: "nobold #f27da4",
        Operator: "#c2b9a8",
        Operator.Word: "bold #ff750f",
        Name.Builtin: "bold #3a96cf",
        Name.Function: "bold #3a96cf",
        Name.Class: "bold #3a96cf",
        Name.Namespace: "bold #3a96cf",
        Name.Exception: "bold #ff5d80",
        Name.Variable: "#f4efe6",
        Name.Constant: "#d8a657",
        Name.Decorator: "#ff750f",
        Name.Attribute: "#3a96cf",
        Name.Tag: "bold #79b473",
        String: "bold #79b473",
        String.Doc: "italic #9a8f7c",
        String.Escape: "bold #ff750f",
        Number: "bold #c490d1",
        Generic.Heading: "bold #f4efe6",
        Generic.Subheading: "bold #3a96cf",
        Generic.Deleted: "#ff6b6b",
        Generic.Inserted: "#79b473",
        Generic.Error: "#ff6b6b",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Generic.Prompt: "bold #9a8f7c",
        Error: "border:#ff6b6b",
    }
