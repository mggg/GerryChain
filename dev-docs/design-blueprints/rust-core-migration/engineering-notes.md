# Engineering guidelines

The stage documents describe what each checkpoint is expected to accomplish. These notes address
the engineering questions that recur across those boundaries: how we represent graph indices,
where ownership passes from Python to Rust, how we manage random streams, and which failures belong
in ordinary control flow.

In my experience, a Rust port can reproduce the expected Python results and still be difficult to
test, unnecessarily coupled to Python objects, nondeterministic, capable of panicking through PyO3,
or slower than the implementation it replaces. Correct outputs on ordinary inputs do not settle the
design.

The central aim is to move complete domain operations into Rust and make their invariants explicit,
without replacing the public Python model or building another graph library. The migration should
reduce, rather than merely relocate, the state that callers and maintainers must keep synchronized
by convention.

## Guiding principle 1: Preserve behavior at the public interface

The baseline defines the observable 1.x behavior that we intend to preserve. Moving an operation
from Python to Rust should not change what callers receive or how supported extension points behave
unless the blueprint calls for the change or an ADR records the deviation. Ordering, warning timing,
callback routing, observable object identity, and random-number consumption all belong to that
contract. Matching only population and connectivity is not sufficient.

In practice:

- Trace the existing Python path before changing it. Record inputs, outputs, ordering, retries,
  callbacks, warnings, exceptions, payload reads, and random draws.
- Add a focused public contract test before switching dispatch to Rust.
- Compare exact results when the algorithm and RNG permit it. Otherwise compare invariants and
  distributions.
- Apply a 1.x contract change uniformly across dispatch paths when the blueprint or an ADR requires
  it.
- Preserve inherited assertions unless the blueprint or an ADR changes the observable behavior.
- Resolve the complete dispatch path before seed derivation. Unsupported graphs, callbacks, or
  inactive prerequisites use the complete Python operation.

## Guiding principle 2: Use types to enforce invariants

Several important distinctions in the Python implementation survive only by convention. A node
index and a district index may both be integers; an incomplete forest and a validated spanning tree
may both be stored as graphs. Treating either pair as interchangeable asks every caller to remember
an invariant that a Rust constructor could establish once and the compiler could then preserve.

We are not trying to reproduce a predetermined catalogue of types. The work is to identify the
baseline's invariants and choose the smallest representations that enforce them. When construction
establishes a relationship, later callers should not have to maintain it by coordinating raw values.

As a rule of thumb, add a type when it does at least one of the following:

- distinguishes values with the same representation but different meanings;
- validates an invariant once for several callers;
- keeps values from one state transition synchronized;
- replaces an invalid combination of booleans or strings with an enum; or
- separates unchecked intermediate state from validated state.

Do not leave an invariant in synchronized vectors or a comment when a type can enforce it.

Prefer the standard library, Petgraph, and existing dependencies before adding another abstraction.

Principles for deriving the type model from the Python behavior:

1. Identify values whose meaning or validity depends on an unwritten convention.
2. Locate every caller that creates or mutates those values.
3. Decide whether an existing type, an enum, a newtype, or a validated struct best represents the
   invariant.
4. Keep fields private when construction must enforce the invariant.
5. Add focused tests for valid boundaries, invalid construction, and state transitions.

Type names and layouts in the blueprint are design sketches rather than required interfaces. A
simpler representation is acceptable when it enforces the same invariant and preserves the same
contract. Changing either requires an ADR.

## Guiding principle 3: Name values by their role and representation

The Python side of the codebase has already begun moving in this direction. The same naming
discipline should extend across the PyO3 boundary.

Names should expose a value's domain role, representation, and lifetime without requiring the reader
to find its definition. The need is most acute at boundaries where the same entity has a Python
label, a rustworkx index, and a dense Rust index.

- Include the index space when it is not obvious: prefer `dense_node_index` or
  `rustworkx_node_index` to `node_id`.
- Use `Snapshot` for an owned, point-in-time representation; use `View` only for a borrowed view
  whose data remains owned elsewhere.
- Use `Workspace` for reusable scratch allocations, `State` for values retained between
  operations, and `Index` for a derived lookup structure.
- Name result enums after the operation and call them `Outcome` when their variants describe
  ordinary control flow. For example, `RecomSearchOutcome` is more informative than
  `SearchResult`.
- Qualify configuration and policy types by the operation they govern. `BipartitionRetryPolicy`
  should not become a general `RetryPolicy` unless several operations actually share its contract.
- Name functions with the operation they perform and the value they return. Avoid bare names such
  as `search`, `extract`, or `update` outside a scope where the object is already unambiguous.
- Keep established GerryChain domain terms when they have one meaning. We do not need to add
  `Rust` to a name merely because the implementation is in Rust.

Short local names such as `graph` and `rng` are appropriate when their meaning is clear from the
function signature. Generic module or type names such as `model`, `data`, `core`, `state`, `result`,
and `id` should either have a domain qualifier or be removed.

## Guiding principle 4: Keep Python at the edge

Python should handle validation, dispatch, and materialization. Once an operation enters Rust, Rust
should ordinarily own its complete control flow.

Python-owned values should remain at the operation boundary. Their presence limits GIL-free
execution, precludes ordinary sharing with worker threads, and makes otherwise ordinary Rust logic
difficult to unit test. Repeated conversion inside an operation also consumes much of the
performance benefit of the port.

PyO3 entry points may validate Python values, extract graph payloads, derive the operation seed,
release the GIL, and translate labels, warnings, exceptions, and return values. Search, retry,
acceptance, and state-transition control flow belongs in Python-free Rust functions.

- Do not access Python values while the GIL is released (i.e. inside a `py.detach` block).
- Do not send Python-owned state to worker threads.
- Represent distinct algorithm outcomes with an enum instead of strings or coordinated booleans;
  map those outcomes to Python at the entry point.
- Extract complete state transitions or search coordinators. Do not create modules around isolated
  arithmetic solely to expose it to tests.

## Guiding principle 5: Return errors instead of panicking

Panics should not cross the PyO3 boundary. They do not correspond to any GerryChain exception, and
a panic while holding a mutex may poison state shared by later calls. Python-free functions should
instead return typed errors, which the PyO3 entry point will translate into the existing Python
exceptions.

Deterministic validation also needs to happen before we derive the Rust seed. Otherwise, a rejected
call consumes eight draws from the caller's RNG despite never beginning the stochastic operation.

- Validate user input before seed derivation.
- Constructors for validated types return `Result`.
- Use `expect`, direct indexing, or assertions only after a private constructor or checked
  operation has established the invariant.
- Treat any panic reachable from accepted Python input as a defect.
- Check dimensions and overflow before allocation. Sparse graph operations should allocate in
  proportion to populated nodes, edges, or keys rather than the full Cartesian product.
- Preserve exception type and failure timing when mapping Rust errors to Python.

## Guiding principle 6: Reuse rustworkx and Petgraph

As the port deepens, I expect it will become tempting to build another graph representation to avoid
the overhead of rustworkx or Petgraph. Borrowing several ideas from RustReCom, which uses its own
representation, will make that temptation stronger. We should resist it. A second topology
representation would add index-synchronization, edge-provenance, memory, and maintenance problems.
Private workspaces will still be necessary, but only for scratch data whose allocation cost is
measurable.

GerryChain expects a simple undirected graph, although the current `Graph` implementation admits
self-loops and parallel edges. We will reject those topologies by default because they fall
outside the model used by GerryChain's algorithms and the surrounding literature. A caller may
retain the old permissive behavior with `allow_unsupported_topology=True` in
`Graph.from_networkx()` or `Graph.from_rustworkx()`. We will continue to reject directed graphs.

Principles for using the existing graph representation:

- Keep the shipped rustworkx/Petgraph graph as the authoritative topology.
- Use Petgraph graphs and algorithms for traversal, spanning trees, and union-find.
- Use `Arc` to share immutable graph state when worker lifetimes require ownership.
- Do not add a second public graph model.

It is fine for a data workspace to retain capacity for local-to-global node mappings (as the Python
implementation currently does), merged populations and edges, Wilson adjacency scratch, region
classes, and worker-local candidate buffers. It must not expose a general graph interface.

Guidelines for workspace reuse:

- Clear every logical buffer before reuse.
- Keep borrowed slices inside the lock or mutable-borrow scope that protects them.
- Copy only data that must survive the operation.
- Test one reused workspace with changing graph sizes, tree algorithms, and region-column counts.

Workspace reuse is most likely to pay off in the parallel ReCom implementation, where each worker
can own its workspace and sampled Petgraph tree while sharing the immutable graph, population
arrays, and accepted assignment.

## Guiding principle 7: Make seeded behavior independent of iteration accidents

The original implementation of RustReCom's parallel reversible runner exposed a subtle problem:
with the same seed and input partition, proposals may nevertheless finish in a different order and
alter the observed trajectory of a run. So, we will make use of the deterministic batching model
that RustReCom added to solve this problem. That model prevents operating-system scheduling and
Rayon work stealing from becoming part of the chain's trajectory.

Candidate order and random-draw ownership must therefore be explicit. Seeded behavior depends on
draw assignment as well as the seed itself; hash-table iteration, graph-index holes, and worker
scheduling can otherwise change a trajectory without changing the underlying probability
distribution. In parallel code, random streams belong to logical batch positions or persistent
logical worker states rather than to physical threads.

- Derive one `ChaCha8Rng` per top-level Rust operation from exactly eight calls to the caller's
  `random.Random.random()`.
- Pass one mutable RNG through every helper. Helpers do not derive additional seeds.
- Use stable node and edge order from the shipped graph.
- Sort unordered candidates before sampling.
- Define one canonical district-pair order and use it for keys and sampling.
- Use `BTreeMap` when sorted iteration affects behavior.
- Use `IndexMap` when first-seen insertion order is public behavior.
- Keep edge payload and provenance on the edge rather than in parallel vectors.
- Do not use `HashMap` or Python set iteration to assign random draws.

Fixed seed, worker count, and batch size reproduce a parallel trajectory. Changing worker count or
batch size may change it. Work stealing or other scheduling differences must not.
