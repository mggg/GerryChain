# Documentation Style Reference

This temporary page collects the common documentation elements in one place so the light and dark
themes can be reviewed without hunting through the user guide.

## Typography

Body text can contain **bold text**, *italic text*, `inline code`,
[external links](https://gerrychain.readthedocs.io/), and {doc}`internal links <../user/install>`.

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

```python
districts = {"north": 5_000, "south": 5_000}
assert sum(districts.values()) == 10_000
```

```console
$ pip install gerrychain
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
:link: ../user/quickstart
:link-type: doc

This card links to the quickstart.
:::

::::

:::{dropdown} Expand this section
Dropdowns keep supporting detail available without making a page harder to scan.
:::

## Badge and image

<a class="download-badge" href="https://github.com/mggg/GerryChain">Example badge</a>

```{image} ../user/images/gerrymandria.png
:alt: Example GerryChain district map
:align: center
:width: 400px
```
