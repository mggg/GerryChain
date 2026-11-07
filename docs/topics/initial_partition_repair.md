# Repairing a disconnected initial partition

`repair_assignment_milp` is an optional initialization utility for analyses in
which a supplied assignment is population-balanced but one or more districts
are disconnected in the graph. It repairs the assignment before constructing a
`MarkovChain`; it does not modify graph edges or replace the supplied plan with
a newly generated plan.

## Model and guarantee

The function identifies the population-largest connected component of each
disconnected district as the retained component. Its interior remains a frozen
anchor; boundary VTDs can enter the movable shell when `border_rings` is
positive. Disconnected components are movable. The shell starts with VTDs on
affected district boundaries and expands by `border_rings` (one ring by
default). All other nodes remain fixed. Binary MILP
variables assign shell nodes to permitted neighboring districts. District-
specific single-commodity flow variables require every assigned shell node to
connect to that district's frozen core. Population constraints apply to every
district, not only affected districts.

For integer node populations, the solver minimizes reassigned population and
then the number of changed VTDs. `optimal_within_model` means the solver found
the optimum for the generated shell, permitted moves, frozen cores, population
range, and connectivity formulation. It is not a global optimum over arbitrary
statewide repartitions.

```python
from gerrychain.partition import repair_assignment_milp

result = repair_assignment_milp(
    graph,
    assignment="CONG_DIST",
    pop_col="total_pop_20",
    pop_target=ideal_population,
    epsilon=0.02,
    border_rings=1,
    max_shell_nodes=2_000,
    time_limit=60,
)

initial_partition = Partition(graph, result.assignment, updaters=updaters)
```

The result records `population_moved`, `nodes_moved`, `changed_nodes`, the
before/after district populations, `shell_size`, and `border_rings`. The caller
should still construct the `Partition` with the same population and contiguity
constraints used by the chain.

`max_shell_nodes` and `time_limit` are safety bounds. A shell-size limit or
solver time limit raises `AssignmentRepairSearchExhausted`; a proven infeasible
MILP raises `AssignmentRepairInfeasible`. This distinction prevents a resource
limit from being reported as proof that no local repair exists.

## Preconditions and failure interpretation

The supplied assignment must already satisfy the requested population range;
this utility is not a separate population-balancing phase. Node populations
must be integer-valued, as in Census population fields. `AssignmentRepairInfeasible`
means that the configured local shell and frozen-core model has no valid repair.
It does not establish that no broader repair exists. Increase `border_rings` or
use a different initialization strategy when a local model is infeasible.

The direct-border shell was infeasible for the exploratory New Mexico graph.
With one ring, the 872-node shell produced a valid two-VTD, 2,343-person repair
at 2% tolerance; independent validation and GerryChain initialization passed.
This state result is exploratory and tied to the documented 2020 graph and
assignment provenance.

## Upstream feedback status

This work is an exploratory, feedback-seeking proposal rather than a
merge-ready feature. The full motivation, proposed one-PR scope, evidence, and
questions for GerryChain maintainers are in
`INITIAL_PARTITION_REPAIR_PR_PROPOSAL.md`. In particular, the motivating use
case comes from road-aware graphs whose overall state graph is connected while
the supplied MCMC districts are not road-contiguous.

Before an eventual merge, maintainers should review the solver dependency and
supported SciPy/HiGHS versions, choose defaults for shell and time limits, and
decide whether this API belongs in core GerryChain or an optional integration.
The utility should remain opt-in rather than changing `Partition` or
`MarkovChain` behavior implicitly.
