# Rust core migration: implementation blueprint

This blueprint describes how we intend to move GerryChain's graph-intensive operations into Rust
without replacing the public Python model or committing ourselves to another graph library. The
work is divided into independently releasable checkpoints, which I created to better fit our
new quarterly release schedule and to prevent an unfinished ReCom port from delaying a tree
implementation that is otherwise ready.

The stage documents contain the algorithm-specific decisions. The engineering notes collect the
rules that should remain consistent across those stages, particularly at the Python boundary and in
code whose result depends on iteration order or random draws.

## Documents and sequence

| Document                        | Purpose                                                                |
| ------------------------------- | ---------------------------------------------------------------------- |
| `engineering-notes.md`          | Shared guidance for types, errors, ownership, and graph reuse          |
| `stage-1-spanning-trees.md`     | Graph extraction, RNG derivation, random and uniform spanning trees    |
| `stage-2-bipartition-engine.md` | Balanced cuts, retry policy, recursive partitioning, random assignment |
| `stage-3-recom.md`              | Standard, multi-member, reversible, and parallel reversible ReCom      |
| `stage-4-partition-state.md`    | Assignment state, lazy transitions, flows, and updater compatibility   |
| `stage-5-cleanup.md`            | 1.x deprecations, 2.0 decisions, and unreachable-code pruning          |

The sequence follows the dependency structure, but the release units are smaller than the stages.
Each stage relies on contracts established earlier; within a stage, however, a completed checkpoint
may ship on its own. A quarterly release candidate can therefore include every complete public
dispatch path while leaving unfinished paths inactive. We gain the benefit of incremental releases
without exposing a partially implemented Rust path.

## Architecture

GerryChain's public Python model will remain in place, with Rust operating behind private PyO3
adapters. Existing callers retain the same interfaces, while a complete graph operation or state
transition can run without repeatedly crossing the Python boundary. Rustworkx and Petgraph will
remain the graph implementation; we do not want to build or maintain another graph library.

```text
Python public interface
    Graph / tree / proposals / Partition / updaters
                    |
                    | validation, dispatch, callbacks, Python object materialization
                    v
private PyO3 adapters in gerrychain-core/src/gerrychain/
                    |
                    | validated Rust values
                    v
Python-free Rust algorithms and state transitions
                    |
                    v
rustworkx / Petgraph graph storage and algorithms
```

## Design references

GerryChain commit `a5eda87e5b7e9ddec1b7d45e482d4c790d6ba539` (after the rustworkx vendor port)
should be treated as the authoritative baseline for the 1.x behavior covered by this blueprint.
RustReCom 0.2.0 at `f551e02fe6abe2b661e8229f6e57cf2ac585b541` demonstrates reusable worker storage
and deterministic parallel batches. It is an implementation reference and point of performance
comparison, not the source of GerryChain's semantics or a release criterion.

Each stage distinguishes among three kinds of work: porting GerryChain behavior, borrowing an
implementation idea from RustReCom, and introducing a GerryChain-specific representation. Those
categories carry substantially different compatibility, validation, and maintenance obligations.

Once implementation begins, we will treat this blueprint as fixed. If implementation work requires
a different design or contract, record the deviation and its rationale in an ADR rather than
rewriting the blueprint to match the implementation.

## Stage document template

Each stage markdown document uses the same organizational structure:

1. **Goal:** the capability delivered and why it belongs in this stage.
2. **Constraints inherited from the baseline:** the behavior that constrains the Rust
   implementation, along with any deliberate departures.
3. **Relationship to RustReCom:** ideas borrowed, ideas rejected, and semantic differences.
4. **Design decisions and tradeoffs:** what each change buys and what it costs.
5. **Proposed implementation:** module ownership, data flow, and stage-specific details.
6. **Implementation checkpoints:** independently activatable increments.
7. **Verification:** correctness, compatibility, reproducibility, and performance checks.
8. **Exit criteria:** the conditions for making a Rust path the default.

Not every distinction will require an extended discussion in every stage. Retaining the structure,
however, keeps the rationale, tradeoffs, and release conditions easy to locate.

## Migration checkpoints

A checkpoint is the smallest unit that can be activated and released independently. Its Rust
prerequisites must already be active or be included in the same release candidate.

| Checkpoint                 | Prerequisites               | Public result                                          |
| -------------------------- | --------------------------- | ------------------------------------------------------ |
| Graph topology validation  | None                        | Unsupported topology is rejected unless bypassed       |
| Random spanning tree       | Graph topology validation   | RX-backed built-in path defaults to Rust               |
| Uniform spanning tree      | Graph topology validation   | RX-backed built-in path defaults to Rust               |
| Bipartition engine         | Selected tree path          | Built-in balanced cuts and retries run in Rust         |
| Recursive partitioning     | Bipartition engine          | Random assignment can stay in one Rust operation       |
| Standard ReCom             | Bipartition + selected tree | Pair selection through transition construction is Rust |
| Multi-member ReCom         | Standard ReCom              | Unequal targets use typed feasible intervals           |
| Reversible ReCom           | Uniform tree + bipartition  | Proposal probability and self-loop behavior match      |
| Parallel reversible runner | Reversible ReCom            | Deterministic batches share immutable graph state      |
| Retained partition state   | Stable proposal result      | Assignment transitions remain Rust-side and lazy       |

### Checkpoint eligibility

A checkpoint can compile and pass focused tests while still leaking dense identifiers, retaining
stale workspace data, changing an unsupported dispatch path, or slowing the package as a whole.
Focused success is therefore necessary but not sufficient. Graph topology validation is the sole
exception to the Rust-dispatch model: it establishes an input contract used by later checkpoints
without activating Rust itself. The dispatch and Rust-specific requirements begin with the tree
checkpoints. Before activating one, verify that:

1. every Rust prerequisite used by its dispatch path is active in the same artifact;
2. its Python dispatcher, when present, resolves the complete path before seed derivation, defaults
   to Rust for supported built-ins, and retains a complete Python fallback for unsupported
   configurations;
3. Rust unit tests cover any new type invariants and Python-free state transitions, and no accepted
   input can reach a panic, poisoned mutex, or unbounded allocation;
4. unchanged Python tests and focused parity, typing, error, callback, and reproducibility tests
   pass;
5. user-visible labels, dictionaries, and sets preserve their required values, shapes, and order;
6. reused workspaces retain capacity without retaining stale logical data;
7. the end-to-end benchmark shows no material regression against the baseline for each supported
   chain path affected by the checkpoint when run under the procedure below; and
8. documentation and the changelog explain observable changes.

An unfinished checkpoint may remain in a release candidate only if it compiles, is unreachable
through normal public dispatch, and adds no public extension symbol. The release candidate as a
whole must also pass the wheel and source-distribution smoke tests, contain one compiled shared
library, and include an accurate Cargo license inventory.

### Benchmark procedure

Performance results are meaningful only relative to the machine and software environment that
produced them. `benchmarks/benchmark_recom.py` and any later benchmark programs define the
workloads, graph fixtures, seeds, run lengths, warmups, repetitions, and reported statistics.

Use the `compare` command to run the same benchmark program against the baseline Git target and the
local implementation. The command installs Git targets in isolated environments and runs every
target with the same workload settings. Use the baseline as the first target so the reported speed
ratio has the intended direction:

```console
uv run python benchmarks/benchmark_recom.py compare \
  git:a5eda87e5b7e9ddec1b7d45e482d4c790d6ba539 local --seed 1234
```

The `micro` command answers a narrower question: which part of a ReCom step is expensive? It runs in
the current environment and separately times graph conversion, random and uniform spanning-tree
construction, balanced-cut search, and one ReCom proposal.

To isolate those operations, the command constructs the tree before timing the balanced-cut search
and constructs the partition before timing ReCom. Every ReCom timing starts from the same partition;
the returned child is discarded rather than used for another step. These measurements can locate a
regression, but they do not represent a chain trajectory.

For each operation, `micro` reports the median and minimum wall-clock time, together with the median
peak Python allocation across the configured repeats. Because the allocation measurement comes from
`tracemalloc`, it cannot see memory allocated in Rust.

Accordingly, `micro` is a diagnostic tool rather than a release gate. A mild slowdown outside the
chain's hot loop does not block a checkpoint when end-to-end throughput remains acceptable. The
end-to-end benchmark should continue to report initial-partition construction so that a material
setup regression remains visible.

The stage documents identify the end-to-end modes that matter to each checkpoint. RustReCom
comparisons are optional external context and do not determine whether a GerryChain checkpoint is
eligible for release.

## Cross-cutting contracts

### Compatibility

Whether an operation ran in Python or Rust should not be a public distinction. Unless this
blueprint identifies an intentional contract change or an ADR records a deviation, the baseline
governs import paths, signatures, accepted inputs, return shapes, documented exceptions and
warnings, callback behavior, arbitrary hashable labels, observable iteration order, and lazy
updater semantics.

Any intentional 1.x contract change specified by this blueprint or an ADR must apply to both the
Python and Rust paths, include focused tests, and be documented in the changelog.

GerryChain expects a simple undirected graph. `Graph` will reject directed graphs, self-loops, and
parallel edges by default. Because earlier versions never rejected self-loops and parallel
edges, callers may preserve that behavior with `allow_unsupported_topology=True` in
`Graph.from_networkx()` or `Graph.from_rustworkx()`. GerryChain does not guarantee algorithm
behavior for those graphs. Directed graphs remain unsupported.

The `gerrychain.rustworkx` compatibility namespace retains the broader rustworkx graph model. Its
graph types may represent directed graphs, self-loops, and parallel edges regardless of whether
they can be used as GerryChain `Graph` objects.

### Reproducibility

The caller-owned Python RNG remains the source of truth. Each top-level stochastic Rust operation
derives one 256-bit ChaCha8 seed from exactly eight calls to the caller-owned
`random.Random.random()`.

Reproducibility is only guaranteed for fixed versions.

### Payloads and the GIL (Global Interpreter Lock)

Repeated dictionary access under the GIL would erase much of the benefit of the Rust port. We will
therefore extract populations and region attributes into Rust-owned arrays before entering an
algorithm loop. We will materialize Python sets, dictionaries, labels, and partition wrappers only
when the public interface requires them.

### Source ownership

Vendored upstream code will remain separate from GerryChain-owned algorithms so future rustworkx
updates remain mechanical and reviewable. GerryChain algorithms belong in
`gerrychain-core/src/gerrychain/`, even when they operate on a `PyGraph`. Record any necessary
change to copied upstream code in `gerrychain-core/src/rustworkx/UPSTREAM.md` and cover it with the
compatibility suite.

### Errors

Expected failures will be represented as data. A Rust panic is not part of the Python API and may
poison shared state, so no accepted Python input may trigger one. PyO3 adapters return `PyErr`
values, while Python-free Rust functions return typed results. Reserve `expect`, direct indexing,
and assertions for invariants established by construction, and cover those invariants with focused
tests.

## Scope

We will move graph-intensive tree algorithms, ReCom variants, partition assignment state, and the
flow computation needed to support existing Python updaters. We will leave the general
`MarkovChain` loop, Python constraints and acceptance callbacks, flip proposals, geometry, metrics,
and updater acceleration in Python for now. A later migration can address scoring and built-in
updaters as a system rather than port them one at a time.
