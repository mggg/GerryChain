# Stage 4: retained partition state, transitions, and flows

## Goal

A successful Rust proposal should not have to materialize a complete Python assignment only for
`Partition` to convert it back into Rust while constructing the child. That round trip would
preserve the public interface, but it would also surrender a meaningful share of the time saved by
running the proposal in Rust. We will therefore retain accepted assignments and the information
needed to construct their children on the Rust side.

`Partition`, `GeographicPartition`, and `Assignment` will remain the public interfaces throughout
1.x. The existing updater system will also remain in Python. This stage will compute the node and
edge flows those updaters need, since recovering them from a fully materialized Python assignment
would recreate much of the round trip we are removing. Accelerating the updaters is a separate
project, which should consider the complete collection of metrics rather than porting them one at a
time.

## Constraints inherited from the baseline

This is an internal representation change and will not fully replace GerryChain's partition model.
`Partition`, `GeographicPartition`, and `Assignment` will continue to accept arbitrary Python
labels, expose the mapping and parts protocols, retain parent and flips information, construct
subgraphs, and evaluate user updaters lazily. A self-loop must also remain observable as the same
partition object. These requirements determine what we materialize at the Python boundary; they do
not require Rust to reproduce the current internal dictionaries.

Updaters will continue to receive the same Python representations they receive today.
`Assignment.parts` remains `dict[part, frozenset[node]]`, `Assignment.mapping` remains
`dict[node, part]`, and node flows remain a mapping from each affected part to its incoming and
outgoing node sets. Parent links, updater exceptions, dictionary insertion order where it affects
behavior, and stable endpoint pairs in edge flows and `neighbor_flips` remain observable.

We will make one deliberate change. Materialized assignment dictionaries become snapshots rather
than mutable stores capable of changing the partition behind the Rust state. This guarantee does
not follow from the baseline, so it requires explicit tests and a changelog entry.

## Relationship to RustReCom

RustReCom already retains the accepted assignment beside the graph in Rust, and we will use the
same basic arrangement. We cannot adopt its partition representation directly, however, because
RustReCom does not need to preserve GerryChain's `Partition` and updater protocols. Our Rust state
will instead sit behind the existing Python interface.

## Design decisions and tradeoffs

- Store the current assignment in Rust and create children from typed transitions. The Python
  facade still reproduces mapping, parts, flips, parent, and updater behavior; the proposal no
  longer takes an assignment-to-dict-to-assignment round trip to get there.
- Keep one complete assignment vector per generation. Each child also retains an `Arc` to its
  immediate parent's complete assignment and the dense node indices that changed. Those values
  support lazy flow calculation without turning the assignments into a chain of delta overlays.
- Materialize Python mappings, part sets, flips, and flows only when requested. Chains that never
  inspect them avoid the allocation; first access pays the conversion cost and must preserve the
  documented shape and order.
- Descendants may share extracted population columns and proposal workspaces, eliminating repeated
  extraction and allocation. The shared ownership introduces locks and GC obligations that must be
  tested explicitly.
- Compute flows from the parent assignment, child assignment, and changed-node indices while
  continuing to return Python dictionaries and sets to updaters. Materializing those containers
  remains a real cost whenever an updater requests them.
- Keep built-in and user-defined updaters in Python. Rust computes flows here because retained
  assignment state would otherwise have to be expanded into complete Python mappings before the
  existing updaters could determine what changed; this is partition-state integration, not an
  updater port.
- Participate in Python's cycle collector. The retained state owns Python references, so ordinary
  reference cycles must remain collectable.

## Proposed implementation

### Domain model

The distinction that matters here is between an assignment and the transition that produced its
child. An assignment only needs to record which part contains each node. A transition, however,
must also record which nodes moved, since `flips` and the flow-based updaters depend on that
history. I would recommend something along the following lines for the internal Rust representation:

```rust
struct DenseAssignment {
    part_index_by_dense_node: Vec<DensePartIndex>,
    occupied_part_count: usize,
}

struct PartitionAssignmentTransition {
    next_assignment: DenseAssignment,
    changed_dense_node_indices: Vec<u32>,
}
```

Construction should establish the part-index invariant once. `DenseAssignment::try_from_indices`
would reject an index outside the label table, and callers update an assignment through checked
methods rather than by writing into the vector. `with_updates` returns the complete child assignment
and its changed-node indices together, which leaves no opportunity for one to be updated without the
other. An update that leaves a node in the same part does not appear in that list.

A Python flips mapping cannot contain the same node twice, and the ReCom transition produces one
update per merged node. Keep that invariant in the transition producers and their tests; there is
no public duplicate-update rule to reproduce.

Stage 3 returns a sparse ReCom delta because a proposal touches only the two selected districts.
Stage 4 applies that delta, or an ordinary Python flips mapping, and produces the complete child
assignment and changed-node list. Python part labels remain in the PyO3 adapter in stable first-seen
order; there is no reason to carry them into the algorithmic state once their dense indices have
been assigned.

### Retained partition state

The simplest arrangement is probably a private PyO3 object that owns the dense assignment and the
Python values needed to reconstruct the public objects. Each child keeps its complete assignment,
an `Arc` to its immediate parent's complete assignment, the nodes changed from that parent, and the
graph and label references required by the Python interface. The graph snapshot, extracted
population columns, and ReCom scratch storage can be shared by every descendant.

That division lets a proposal construct its child without passing through an assignment dictionary,
but it does not ask callers to learn a second partition interface. I would begin with roughly this
ownership model:

```rust
#[pyclass(unsendable)]
struct PartitionState {
    python_graph: Option<Py<PyGraph>>,
    graph_snapshot: Arc<DenseGraphSnapshot>,
    python_part_label_by_dense_index: Vec<Py<PyAny>>,
    dense_assignment: Arc<DenseAssignment>,
    population_by_column: Arc<Mutex<HashMap<String, Arc<Vec<f64>>>>>,
    recom_scratch: Arc<Mutex<RecomScratchWorkspace>>,
    parent_dense_assignment: Option<Arc<DenseAssignment>>,
    changed_dense_node_indices: Vec<u32>,
}
```

The `Arc` fields are for data that descendants actually share. Neither the graph snapshot nor an
assignment needs a lock. The population cache does, but only during lookup or insertion, and the
lock can be released before ReCom begins. The scratch lock necessarily remains held while ReCom
mutates the workspace and should be released before materializing a Python result. A smaller field
layout is welcome if it preserves those ownership rules.

The current and parent assignments are both complete vectors. The parent `Arc` and
`changed_dense_node_indices` provide the one-generation snapshot needed for lazy flow calculation;
neither vector points to an earlier assignment. A child still costs one vector copy, but every
node-to-part lookup remains constant-time and no lookup traverses the partition ancestry.

The Python references bring one additional obligation. PyO3 must expose the graph and part labels
to Python's cycle collector and clear them when `PartitionState` is collected. GC tests should
clear the existing `lru_cache` first, since its documented retention of partition identities can
otherwise look like a cycle in the Rust state.

`PartitionState` remains unsendable while it owns Python objects. Parallel workers receive the
Python-free graph snapshot, dense assignment, and attribute arrays instead.

### Python interface and lazy materialization

The Rust assignment can be authoritative without making that fact burdensome for users. Python
mappings, sets, flips, and flows will be constructed only when a caller asks for them. Chains that
do not inspect those objects avoid the allocation, while existing code continues to receive the
same Python types.

`Assignment.mapping` becomes a dictionary on first access, and `Assignment.parts` becomes a
`dict[label, frozenset[node]]` on first access. `partition.flips` remains a plain dictionary, but a
Rust proposal may defer its construction and pass a `PartitionAssignmentTransition` directly to
the child. The Python classes continue to manage parent access, `__getitem__`, subgraphs, updater
invocation, and updater-result caching.

Snapshot semantics are the right 1.x correction here. The baseline permits callers to mutate
`mapping` and `parts` independently, at which point the two views of an assignment can disagree.
The documented dictionary shapes remain, but their contents cease to be mutable partition state.
Assignment lookup, updater evaluation, and child construction continue to read from Rust, so
changing a previously returned dictionary has no effect on the partition. The changelog should say
so plainly.

`SubgraphView.parts` must remain a part-to-node-set mapping rather than expose the internal
`Assignment`. A flip to a label absent from the part-label table must also raise the same
exception as today; it must not create a new dense part implicitly.

### Pure flow computation

Flow calculation does not need Python. Given the complete parent and child assignments and the
changed-node indices, it can read the previous and new part for every endpoint and return incoming
and outgoing dense node or edge indices grouped by part. The PyO3 adapter constructs the existing
dictionaries and sets only when an updater requests them; the calculation itself remains an
ordinary Rust function that can be tested without `Partition` or the GIL.

The outer node-flow mapping needs the order in which parts are first encountered rather than sorted
or hash-table order. `IndexMap` is a natural fit. The inner collections deserve a closer look at
their consumers: Python does not guarantee set order across processes, but changing the
construction order can still affect code that iterates a set within one process. Preserve that
order wherever it can alter a seeded decision.

The changed-node list contains a node only when its parent and child parts differ. Edge-flow tests
must cover edges with one changed endpoint and two changed endpoints, including the case in which a
single edge appears in the boundary changes for two parts. Do not count either entry twice.

### Population cache

Caching population columns requires a decision about graph mutation. A column can be extracted once
and shared with every descendant, but only while the underlying node attributes stay fixed. Although
callers can currently reach those dictionaries through `partition.graph`, there is no notification
or version counter from which to build reliable cache invalidation.

The simpler rule is to make graph-payload mutation unsupported while a partition or any descendant
remains live, rather than design an invalidation system for this migration. This is an intentional
1.x change and needs to be documented. The cache itself remains modest: it maps an attribute name
to a shared Rust array, and its mutex is held only for lookup or insertion. ReCom releases the lock
before beginning the search. Later support for live payload mutation will require an explicit
invalidation design and an ADR.

### Future updater migration

The long-term updater architecture should not be settled as a side effect of moving partition state
into Rust. GerryTools gives us a better model for that work through its
[PlanEvaluator](https://gerrytools.readthedocs.io/en/stable/user/scoring/plan_evaluator/).
It prepares graph and geometry resources once, evaluates a registered collection of metrics in
compiled code, and caches the combined result on the partition. Recorded assignments can also be
scored in batches. This model amortizes data extraction and Python-boundary costs across several
metrics and plans rather than treating each updater as an isolated call.

When we return to updater performance, the first distinction should be between values needed during
the chain and scores used only for analysis. Constraints and proposals need their inputs at each
transition and may benefit from incremental updates to retained assignment state. Analytical scores
can instead be evaluated in batches, including from a recorded chain. The design will need to cover
metric registration, shared prepared resources, evaluation of several metrics in one Rust call,
and coexistence with arbitrary Python updaters. For this migration, the requirement is narrower:
preserve the existing updater contract and provide its flow inputs without forcing the complete
assignment back through Python.

## Implementation checkpoints

1. Add validated `DenseAssignment`, `PartitionAssignmentTransition`, and pure transition tests.
2. Build `PartitionState` from an RX-backed graph and existing Python assignment.
3. Advance children through typed transitions while keeping all public objects unchanged.
4. Add lazy mapping, parts, flips, and proposal-core handoff.
5. Add pure node and edge flows, then connect the existing Python wrappers.
6. Add GC and long-parent-chain coverage.

Each checkpoint retains the existing Python fallback or facade until its complete behavior is
covered. Do not mix public cleanup into core-state migration.

## Verification

### Correctness and compatibility

- Assignment rejection of unknown parts and out-of-range dense indices.
- Child transition parity for no-op, one-node, multi-node, and repeated flips.
- Mapping and parts shape, insertion order, mixed labels, and materialization caching.
- Mutating a materialized mapping or parts snapshot does not change assignment lookup, updater
  results, or later child construction.
- Node and edge flow parity, including parts with only incoming or outgoing changes.
- `FrozenGraph` wrapping NX and RX backing.
- Reference cycles, GC traversal, clearing, and documented cache retention.
- Lazy transition data after parent detachment.
- Rust proposal handoff without Python dict round trips.
- Existing arbitrary updater values and exceptions.
- A newly constructed partition observes graph payload changes made before its construction; live
  partitions and their descendants make no guarantee about later payload mutation.

### Performance checks

Use the end-to-end comparison in `benchmarks/benchmark_recom.py` before activating retained state.
The benchmark already reports initial-partition construction separately. Use profiling or add an
isolated measurement only when the end-to-end result needs explanation. Treat Python allocation
peaks as Python-object churn, not Rust memory.

Parent-chain memory must be no worse than the Python full-mapping copy. Retain an allocation cache
or delta representation only when the paired end-to-end benchmark shows a material improvement.

## Exit criteria

Ordinary partition construction and advancement use the Rust core by default, while existing Python
and user updaters observe the same public values and lifecycle. Transition data remains lazy;
Python can collect reference cycles; and chain throughput and memory show no material regression.
