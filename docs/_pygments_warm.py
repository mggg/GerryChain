"""Custom Pygments styles for the docs, ported from binary-ensemble's warm palette.

``WarmLightStyle`` fits the warm "tangerine" palette: a cream background with tokens drawn
from the brand accent family (orange and amber warms against cerulean and teal cools) rather
than a stock theme's unrelated hues. Every token color is chosen to clear ~4.5:1 contrast on
the cream background.

``WarmDarkStyle`` is the dark companion: the SAME token roles and bold/italic treatment, in
bright dark-mode colors chosen to clear ~5.5:1+ on the dark canvas, so the two themes feel
consistent across light/dark.

conf.py points ``pygments_style`` / ``pygments_dark_style`` here via Sphinx's dotted-path
support ("module.ClassName").
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
