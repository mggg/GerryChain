# Evaluating districting plans in the real world

GerryChain is used to analyze redistricting plans in the real world. For example, it's
been used in states ranging from Pennsylvania to North Carolina to Wisconsin for
defend civil rights. So, [MGGG] has developed a toolkit of functions for use to analyze
a redistricting plan. Here, we will describe these tools and how they are used to
analyze real-world districting plans.

## gerrytools

[gerrytools] is a toolkit that contains:

- a suite of plan scoring metrics (like efficiency gap and reock scores) for use in
  comparing plans
- a suite of data grabbing/manipulating tools, with an emphasis on interacting with
  Census data
- super-easy and beautiful visualization functions to make pretty graphs and intuitive
  displays of data
- miscellaneous things we find useful

It also has fairly good documentation, which you can read here: <https://gerrytools.readthedocs.io/>

## PyEI

[PyEI] is a ecological inference package in Python that is intended for racial
polarized voting analysis. This analysis is required for Voting Rights Act challenges of
gerrymandered redistricting maps. As such, [PyEI] is essential to [MGGG]'s work.

## Other tools

There are also other tools used in redistricting workflows, including [maup] and
[Binary Ensemble], which have their own documentation. Binary Ensemble stores,
compresses, and streams ensembles of districting plans.

[gerrytools]: https://github.com/mggg/gerrytools
[maup]: https://github.com/mggg/maup
[mggg]: https://mggg.org
[binary ensemble]: https://binary-ensemble.readthedocs.io/
[pyei]: https://github.com/mggg/ecological-inference
