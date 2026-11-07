# Feedback request: repairing disconnected initial assignments before MCMC

## Status

This is an exploratory proposal seeking feedback from GerryChain maintainers and
users. It is not presented as merge-ready. The goal is to determine whether an
opt-in initial-assignment repair utility would be a reasonable GerryChain
integration, and what API, solver, and modeling changes would be needed before
an eventual contribution.

## Motivation

I have been working on road-aware dual graphs for redistricting analyses. In
some experiments, the roadgraph state graph is fully connected: the graph
itself has one component under the road-adjacency rules. However, when an
enacted or supplied congressional assignment is applied to that graph, one or
more induced districts are not connected by the graph. In other words, the
districts are not necessarily “road contiguous,” even though the overall state
graph is connected.

This matters before MCMC starts. GerryChain's contiguity and population
constraints apply to the initial partition, so an assignment that is valid as a
table of district labels may not be a valid `MarkovChain` initial state.

The proposed utility would repair that assignment downstream, without adding
roadgraph edges to accommodate a particular plan.

## Proposed one-PR scope

The current branch explores one graph-agnostic contribution containing:

1. Assignment diagnostics and validation utilities for coverage, population,
   and induced contiguity.
2. An opt-in MILP repair function for a disconnected initial assignment.
3. Focused synthetic tests, including multi-district exchanges and explicit
   infeasibility/search-exhaustion behavior.
4. Documentation of the model, its guarantee, and its limitations.

This would not change `Partition` or `MarkovChain` behavior implicitly. A user
would call the repair utility explicitly and then construct a `Partition` from
the returned assignment.

The older bounded backtracking implementation remains in this experimental
checkout as development history and a comparison point. It should not
automatically be included in the one-PR proposal unless maintainers specifically
want both repair backends; the proposed contribution is centered on the
solver-backed local model.

## Proposed model

The solver identifies the population-largest connected component of each
disconnected district as the retained component. Its interior is a frozen
anchor. Disconnected fragments and VTDs on affected district boundaries form a
movable shell; one additional graph border ring is the current default, with
zero or larger values available explicitly.

Binary variables assign shell nodes to permitted neighboring districts. Linear
population constraints enforce the requested tolerance. District-specific
single-commodity flows require every assigned shell node to connect to its
district's retained anchor. The objective minimizes reassigned population and
then the number of changed VTDs.

The guarantee is deliberately bounded:

> The solver finds the minimum-population repair within the generated shell,
> frozen anchors, permitted moves, population bounds, and connectivity model.

It does not prove a global optimum over arbitrary statewide repartitions.

## Current evidence

The experimental implementation has been checked with:

- focused synthetic repair tests;
- exhaustive comparisons on deterministic small graphs, where the MILP result
  matched the optimum inside the generated shell;
- independent contiguity and population validation;
- GerryChain `Partition` and `MarkovChain` initialization.

On an exploratory New Mexico roadgraph output built from 2020 Census/RDH data,
the direct-border shell was infeasible at 2% population tolerance. A one-ring
shell produced an 872-node model and a valid repair changing two VTDs and 2,343
people. This result is evidence about the proposed local model, not a claim
about all roadgraphs or all assignments.

## Questions for feedback

1. Is this a reasonable GerryChain integration point, or should this remain an
   external helper around `Partition` and `MarkovChain`?
2. Is a solver-backed MILP appropriate as an optional GerryChain utility?
3. Should the API expose the shell/ring model directly, or should candidate
   selection be supplied by the caller?
4. Are frozen anchors and local shell restrictions an acceptable basis for an
   optimality claim?
5. Should infeasibility and solver exhaustion use the proposed exception
   distinction?
6. Which SciPy/HiGHS versions and runtime limits would be acceptable?
7. Should the public API return a structured audit result, or only an
   assignment plus diagnostics?

## Deliberate non-goals

This proposal does not modify roadgraph construction, add graph edges, generate
new initial plans, or claim that a repaired assignment is the enacted plan. The
roadgraph-specific state files and provenance remain outside the GerryChain
contribution; they motivate the problem and provide exploratory validation.
