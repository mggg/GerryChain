---
orphan: true
---

# Documentation Style Reference

This temporary page collects the common documentation elements in one place so the light and dark
themes can be reviewed without hunting through the user guide. It isn't part of the site
navigation — open it directly at `/style_reference/` (locally,
`http://localhost:8000/style_reference/`).

To compare palettes and code themes live, build with the switcher enabled —
`DOCS_SWITCHER=1 make docs-serve` — then use the 🎨 (palette) and `</>` (code theme) dropdowns,
flipping Furo's light/dark toggle to check each combination in both modes.

## Typography

Body text can contain **bold text**, *italic text*, `inline code`,
[external links](https://gerrychain.readthedocs.io/), and {doc}`internal links <user/install>`.

### Third-level heading

#### Fourth-level heading

> A block quote shows how quoted prose, wrapping, and spacing look together.

- An unordered list item
- Another item with nested content

  1. First nested item
  2. Second nested item

1. A numbered list item
2. Another numbered item

---

## Admonitions

:::{note}
This is a note. It uses the blue selected for general documentation callouts.
:::

:::{admonition} Coding Note
:class: note

This is a titled note, matching callouts that need a more specific label.
:::

:::{attention}
This is an attention callout.
:::

:::{caution}
This is a caution callout.
:::

:::{danger}
This is a danger callout.
:::

:::{error}
This is an error callout.
:::

:::{hint}
This is a hint callout.
:::

:::{important}
This is an important callout.
:::

:::{seealso}
This is a see-also callout.
:::

:::{tip}
This is a tip callout.
:::

:::{warning}
This is a warning callout.
:::

## Code

A console block, then a snippet that exercises every common syntax-highlighting token so the
active code theme can be eyeballed at a glance. **What to look at:** comments, strings, numbers,
function names, keywords (`def`/`class`/`for`/`return`), builtins + `True`/`False`/`None`,
**bold** module names, decorators, operators, and exceptions.

```console
$ pip install gerrychain
```

<!-- docs-test: skip -- display-only token sampler; not a runnable example -->
```python
#!/usr/bin/env python
"""Module docstring — a syntax-highlighting token sampler."""
from __future__ import annotations

import os
from collections import OrderedDict as Ordered  # import, module name, alias

GREETING: str = "hello\tworld\n"     # string + escapes + type annotation
PI = 3.14159                         # float
MASK = 0xFF | 0b1010                 # hex, binary, bitwise operator
WHERE = 1 + 2j                       # complex number


@property                            # decorator
def shout(text):
    """Return *text* uppercased."""  # docstring
    return f"{text.upper()}!"        # f-string interpolation + builtin call


class Sampler(Exception):            # class name, exception base
    """A tiny demo class."""

    LIMIT = 100

    def __init__(self, name=None):
        self.name = name or "anon"   # operator-word `or`, None, attribute

    def run(self, steps: int) -> list[int]:
        out = [n * 2 for n in range(steps) if n % 2 == 0]  # comprehension, builtins, ops
        try:
            assert steps > 0 and steps is not None         # and / is / not
        except ValueError as err:                          # exception name
            raise Sampler("bad") from err
        return out


square = lambda x: x ** 2 if x else None   # lambda, **, if/else, None
print(shout("hi"), True, False, os.name)   # builtins, True/False, attribute
```

## Tables

| Element | Example | Status |
| --- | ---: | :---: |
| Population | 10,000 | Ready |
| Districts | 4 | Ready |

## Cards and dropdowns

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Example card

Cards are used for prominent navigation and grouped choices.
:::

:::{grid-item-card} Linked card
:link: user/quickstart
:link-type: doc

This card links to the quickstart.
:::

::::

:::{dropdown} Expand this section
Dropdowns keep supporting detail available without making a page harder to scan.
:::

## Badge and image

<a class="download-badge" href="https://github.com/mggg/GerryChain">Example badge</a>

```{image} user/images/gerrymandria.png
:alt: Example GerryChain district map
:align: center
:width: 400px
```
