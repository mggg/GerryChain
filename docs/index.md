---
sd_hide_title: true
---

# GerryChain

```{div} sd-text-center sd-fs-2 sd-font-weight-bold
GerryChain
```

```{div} sd-text-center sd-fs-5 sd-text-secondary
Build and analyze ensembles of districting plans with Markov chain Monte Carlo.
```

---

```{image} https://readthedocs.org/projects/gerrychain/badge/?version=latest
:alt: Documentation Status
:target: https://gerrychain.readthedocs.io/en/latest
```

```{image} https://badge.fury.io/py/gerrychain.svg
:alt: PyPI Package
:target: https://pypi.org/project/gerrychain/
```

:::{admonition} 1.0.0 Release
:class: important

A RELEASE HAPPENED AND THERE IS STUFF TO READ. FINISH LATER.
:::

GerryChain is a library for using [Markov Chain Monte Carlo](https://en.wikipedia.org/wiki/Markov_chain_Monte_Carlo)
methods to study the problem of political redistricting. Development of the
library began during the 2018 Voting Rights Data Institute (VRDI).

The project is in active development in the [mggg/GerryChain](https://github.com/mggg/GerryChain)
GitHub repository, where [bug reports and feature requests](https://github.com/mggg/gerrychain/issues),
as well as [contributions](https://github.com/mggg/gerrychain/pulls), are welcome.

## Install

Most users can install GerryChain using pip:

```console
pip install gerrychain
```

For more detailed installation instructions, including instructions for
setting up virtual environments, please see the following section:
{doc}`user/install`.

## Where to next

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} {octicon}`rocket` Getting started
:link: user/quickstart
:link-type: doc

Install the package and run your first chain on Pennsylvania's VTDs.
:::

:::{grid-item-card} {octicon}`mortar-board` User guide
:link: user/intro
:link-type: doc

Executable notebook guides with rendered outputs, from the anatomy of the chain
through ReCom, real data, geometries, and optimization.
:::

:::{grid-item-card} {octicon}`light-bulb` Topics
:link: topics/reproducibility
:link-type: doc

Reproducibility practices, companion tools, and how to contribute or report issues.
:::

:::{grid-item-card} {octicon}`code` API reference
:link: api
:link-type: doc

Every public class and function in `gerrychain`, organized by module.
:::

::::

We also highly recommend the resources prepared by Daryl R. DeFord of
MGGG for the 2019 MIT IAP course
[Computational Approaches for Political Redistricting](https://people.csail.mit.edu/ddeford//CAPR.php).

```{toctree}
:hidden:
:caption: User Guide
:maxdepth: 1

user/intro
user/install
user/quickstart
user/recom
user/partitions
user/updaters
user/data
user/geometries
user/optimizers
user/geometric_optimizers
```

```{toctree}
:hidden:
:caption: API Reference
:maxdepth: 2

api
```

```{toctree}
:hidden:
:caption: Topics
:maxdepth: 1

topics/v1p0p0_migration_guide
topics/reproducibility
topics/tools
topics/contributing
topics/reporting
```
