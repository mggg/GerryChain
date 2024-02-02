==============================================
Evaluating districting plans in the real world
==============================================

GerryChain is used to analyze redistricting plans in the real world. For example, it's
been used in states ranging from Pennsylvania to North Carolina to Wisconsin for
defend civil rights. So, `MGGG`_ has developed a toolkit of functions for use to analyze
a redistricting plan. Here, we will describe these tools and how they are used to
analyze real-world districting plans.


gerrytools
----------
`gerrytools`_ is a toolkit that contains:

- a suite of plan scoring metrics (like efficiency gap and reock scores) for use in
  comparing plans
- a suite of data grabbing/manipulating tools, with an emphasis on interacting with
  Census data
- super-easy and beautiful visualization functions to make pretty graphs and intuitive
  displays of data
- miscellaneous things we find useful

It also has fairly good documentation, which you can read here: https://mggg.github.io/gerrytools/

PyEI
----
`PyEI`_ is a ecological inference package in Python that is intended for racial
polarized voting analysis. This analysis is required for Voting Rights Act challenges of
gerrymandered redistricting maps. As such, `PyEI`_ is essential to `MGGG`_'s work.


Other tools
-----------
There are also other tools maintained by `MGGG`_, including `maup`_ and
`pcompress`_, which have their own set of documentation.

.. _`MGGG`: https://mggg.org
.. _`gerrytools`: https://github.com/mggg/gerrytools
.. _`PyEI`: https://github.com/mggg/ecological-inference
.. _`maup`: https://github.com/mggg/maup
.. _`pcompress`: https://github.com/mggg/pcompress
