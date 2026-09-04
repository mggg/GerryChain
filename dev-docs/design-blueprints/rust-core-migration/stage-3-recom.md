# Stage 3: ReCom proposals as single Rust operations

## Goal

Standard, multi-member, and reversible ReCom constitute three separate checkpoints. In each case, a
proposal will run as one Rust call encompassing pair selection, merged-subgraph construction, tree
sampling, cut selection, and transition construction. A fourth, optional checkpoint adds a
deterministic parallel runner for reversible chains.

The full proposal, rather than an isolated tree sampler or balanced-cut search, is the relevant
performance unit for this stage, and we will avoid a narrower port since that would still rebuild
merged graphs and convert assignments at several Python/Rust crossings.

## Constraints inherited from the baseline

The Rust proposal must preserve the two district-pair distributions. `"district_pairs"` chooses
uniformly among adjacent district pairs, while `"cut_edges"` weights a pair by the number of edges
along its shared boundary. District-pair selection must also be deterministic for a fixed
GerryChain version and RNG seed; it cannot depend on `PYTHONHASHSEED`, Rust hash-table iteration, or
whether the district labels are mutually comparable. The particular Python machinery used
to establish that order does not need to survive the port.

Standard ReCom tries candidate pairs without replacement. A failed bipartition advances to the next
pair, and failure across the complete sequence raises `MetagraphError` with the existing message.
Once a cut succeeds, the split must retain which of the two district labels belongs to each side;
canonical ordering used for map keys must not erase that assignment.

Multi-member ReCom uses the same pair-selection and retry rules, but the admissible population range
must satisfy both district targets. An empty intersection continues to raise
`PopulationBalanceError`.

Reversible ReCom has a different proposal kernel, and the Rust implementation must preserve its
balanced-cut count, `max_balanced_edge_cuts` bound, seam-length acceptance probability, and
self-loop rules. A tree with no balanced cut produces a self-loop unless `repeat_until_valid`
instructs the coordinator to try again.

All three variants accept arbitrary hashable district labels and retain the existing warnings and
reselection failures. A custom callable at any supported extension point routes the complete
proposal through Python.

## Relationship to RustReCom

Matching or nearly matching RustReCom's implementation is not a goal since its RNG, pair-selection,
cut-selection, retry, and self-loop rules differ from GerryChain's.

The optional parallel reversible runner does borrow RustReCom's high-level execution model. Workers
share the immutable parent graph and assignment, build the selected two-district graph in reusable
worker-local storage, and sample worker-local trees. Complete batches can therefore be computed
without copying the parent graph for each worker.

GerryChain imposes two additional constraints. First, the ordinary proposal API must continue to
produce Python `Partition` objects and support Python callbacks through fallback. Second, workers
should not rescan the full graph for every attempt; a shared index of district membership and edge
categories may therefore be rebuilt after accepted transitions. That index is assignment state,
not another representation of the topology.

## Design decisions and tradeoffs

- Pair selection, tree sampling, cut search, retries, and transition construction belong in one
  Rust call. Repeated conversion and GIL acquisition then disappear from the proposal loop; direct
  Python-free tests cover its internal outcomes.
- Store adjacent district pairs sparsely so memory follows graph edges rather than the square of the
  district count. Maintaining the map or index is preferable to an allocation that can become
  quadratic for a valid partition.
- Keep Python labels outside detached and worker state. Rust storage uses compact, thread-safe dense
  identifiers, while a stable first-seen label table restores the public values at the boundary.
- Begin with fresh allocations. Reusable workspaces follow only after the implementation is correct
  and a benchmark shows that reuse helps. Wilson-tree and reversible workloads are plausible
  beneficiaries, whereas a random-MST proposal may gain nothing from the additional reset and
  locking machinery.
- Begin with a dedicated parallel reversible runner rather than changing general `MarkovChain` in
  the same checkpoint. Its first version supports only proposal and acceptance rules that can run
  in Rust. We may apply the same batching model to general chains later, once custom acceptance and
  rejection functions have a defined interface.
- Treat worker count and batch size as trajectory inputs. A fixed configuration is reproducible;
  changing the parallel decomposition may change the chain.
- Materialize Python children and updater inputs lazily. A chain that never inspects them avoids the
  conversion, while first access continues to produce the same Python objects as before.

## Proposed implementation

### Domain model

Dense part indices, canonical pair keys, split-side assignments, complete assignments, and accepted
transitions share an integer representation. Their ordering and validity rules differ,
however, and the Rust types should preserve those distinctions.

```rust
struct DensePartIndex(usize);
struct SplitSidePartIndices {
    selected_side: DensePartIndex,
    complement_side: DensePartIndex,
}
struct CanonicalPartIndexPair(DensePartIndex, DensePartIndex);
struct DenseAssignment {
    part_index_by_dense_node: Vec<DensePartIndex>,
    occupied_part_count: usize,
}
struct RecomAssignmentDelta {
    part_index_updates_by_dense_node: Vec<(usize, DensePartIndex)>,
}

enum RecomSearchOutcome {
    TransitionFound {
        assignment_delta: RecomAssignmentDelta,
        bipartition_warning_count: usize,
    },
    CandidatePairsExhausted { bipartition_warning_count: usize },
    TreeAttemptLimitReached { bipartition_warning_count: usize },
    PairPopulationInfeasible {
        part_pair: CanonicalPartIndexPair,
        first_part_range: FeasiblePopulationRange,
        second_part_range: FeasiblePopulationRange,
    },
}
```

`CanonicalPartIndexPair` serves selection, deduplicated map lookup, and boundary-edge counting; at
that point, neither district is first in the proposal. Once a balanced cut distinguishes the two
sides, `SplitSidePartIndices` records which district label belongs to the selected tree side and
which belongs to its complement. `DenseAssignment` validates every part index once, whereas
`RecomAssignmentDelta` contains only the assignments that changed. Warning counts are search
history, not partition data, and therefore belong to the outcome. Python labels remain in an
adapter-owned table until the public result is materialized.

Each multi-member district has a valid interval of its own even when the two intervals do not
intersect. An infeasible outcome retains both ranges rather than mischaracterize their empty
intersection as a `FeasiblePopulationRange`.

### Partition snapshot

The ReCom search receives one Python-free snapshot containing everything required by the proposal.
Before retained partition state exists, each proposal must extract that snapshot from the Python
`Partition`. We can pay for that extraction once, before entering a GIL-free search that contains no
Python-owned labels.

```rust
struct RecomPartitionSnapshot {
    graph_snapshot: Arc<DenseGraphSnapshot>,
    dense_assignment: Arc<DenseAssignment>,
    population_by_dense_node: Arc<Vec<f64>>,
    region_class_by_attribute_and_node: Vec<Vec<Option<usize>>>,
    region_surcharge_by_attribute: Vec<f64>,
}
```

The PyO3 adapter separately retains the first-seen Python label table. First-seen label order
defines `DensePartIndex` rank and, therefore, canonical district-pair order. After the partition
state checkpoint, snapshot construction becomes shared Rust state without changing the search
interface.

### Candidate-pair sequencing

The two public pair-selection rules assign different probabilities and should not be collapsed into
one loosely configured iterator. District-pair mode shuffles adjacent pairs once; cut-edge mode
repeatedly weights untried pairs by their shared boundary length. Both retain the selected pair in
canonical form. Only after a balanced cut distinguishes the selected tree side from its complement
do we create `SplitSidePartIndices`.

```rust
enum CandidatePartPairSequence {
    Shuffled {
        part_pairs: Vec<CanonicalPartIndexPair>,
        next_pair_index: usize,
    },
    CutEdgeWeighted {
        part_pair_cut_edge_counts: Vec<(CanonicalPartIndexPair, usize)>,
        tried_pair_indices: FixedBitSet,
    },
}
```

Let's use a sparse `BTreeMap<CanonicalPartIndexPair, usize>` or another index whose storage is
proportional to graph edges and occupied adjacent pairs just in case someone tries to run a
1000-district partition on a 10,000-node graph (I have seen stranger things).

### Standard ReCom

Pair selection, merged-graph construction, tree sampling, cut search, and transition construction
will run as one Rust operation. Repeated GIL acquisition then disappears from the retry loop, and
one proposal cannot mix the Python and Rust RNG streams.

For each candidate pair:

1. Build a merged view over nodes assigned to either part, with a local-to-global node table.
2. Sample the selected built-in Petgraph tree using the proposal's one RNG stream.
3. Run the Stage 2 balanced-cut engine with pair reselection enabled.
4. Convert a failed pair into an internal reselection outcome rather than a Python exception.
5. Build a typed `RecomAssignmentDelta` in full-graph dense node indices.
6. Map the split to Python labels only after Rust returns.

A plausible Python-free search interface is:

```rust
fn search_recom_transition(
    partition: &RecomPartitionSnapshot,
    config: &RecomSearchConfig,
    rng: &mut ChaCha8Rng,
    scratch: &mut RecomScratchWorkspace,
) -> RecomSearchOutcome;
```

No Python value may be accessed while the search runs with the GIL released.

Until retained partition state lands, the PyO3 adapter should convert an accepted
`RecomAssignmentDelta` to the flips dictionary consumed by `partition.flip()`. Stage 4 introduces a
separate partition transition containing the complete next assignment and its changed-node list.
At that point, Rust can apply the ReCom delta directly and hand the resulting transition to the
child partition without an assignment-to-dict-to-assignment round trip.

Variant routing must be resolved before Rust is entered. MST variants require the random-tree and
bipartition checkpoints; UST variants require the uniform-tree and bipartition checkpoints. A
custom callable or inactive prerequisite sends the entire proposal through Python.

### Multi-member ReCom

Multi-member ReCom reuses the standard search, changing only the population-feasibility
calculation. Pair selection, tree sampling, and transition behavior should remain identical. For
each pair, derive an inclusive `FeasiblePopulationRange` satisfying both target tolerances; an empty
intersection raises `PopulationBalanceError` as before.

Do not represent the derived range as user-facing `PopulationTargetTolerance`. Handle zero-width
ranges, including `[0, 0]`, without `expect` or panic.

### Reversible ReCom

Reversible ReCom requires its own coordinator because balanced-cut counts, seam-length acceptance
probabilities, and self-loop rules define a different proposal kernel. It can share tree and
cut-search machinery with standard ReCom without sharing its control flow.

We should add proposal-probability and cut-count fixtures before implementing this checkpoint.
Reversible ReCom uses a uniform spanning tree, Stage 2's count of balanced cuts, the
`max_balanced_edge_cuts` bound, and seam-length acceptance arithmetic. No balanced edge produces a
self-loop. Preserve `repeat_until_valid=False` short-circuiting and warning behavior.

Proposed typed result to return:

```rust
enum ReversibleProposalOutcome {
    TransitionAccepted {
        assignment_delta: RecomAssignmentDelta,
        bipartition_warning_count: usize,
    },
    SelfLoop { bipartition_warning_count: usize },
    BalancedCutLimitExceeded {
        balanced_cut_count: usize,
        bipartition_warning_count: usize,
    },
}
```

Retry and acceptance control flow also belong to the reversible coordinator, not the Python adapter.

### Scratch workspace and graph ownership

This is the most useful idea that we are going to borrow from RustReCom. The rustworkx/Petgraph
graph, payload arrays, and accepted assignment remain authoritative. A private
`RecomScratchWorkspace` may retain allocations for merged node indices, populations, edges,
adjacency, and region classes. Workers and successive proposals can then reuse capacity without
creating another graph abstraction; sampled trees remain ordinary Petgraph `UnGraph` values.

The workspace must:

- clear every logical buffer before reuse while retaining allocation capacity;
- expose borrowed slices only while its lock or mutable borrow is held;
- copy only accepted split assignments into the result;
- survive partition-parent detachment through shared ownership; and
- remain private scratch storage rather than another graph interface.

### Deterministic parallel reversible runner

The first parallel runner will target reversible ReCom because its proposal and acceptance rules can
already run entirely in Rust. That restriction is a practical starting point rather than a permanent
limitation on `MarkovChain`; once we have a suitable interface for custom acceptance and rejection
functions, the same execution model may support more general chains.

The speedup comes from evaluating likely self-loops speculatively. Every worker starts from the same
parent graph, population arrays, and accepted assignment, all of which remain immutable while the
batch is running. Each worker samples a proposal using its own scratch space and Petgraph tree. The
coordinator then reads the results in proposal order. A rejected proposal accounts for one chain
position but leaves the parent unchanged, so the next result in the batch is still valid. The first
accepted proposal becomes the new parent, at which point the unused tail must be discarded because
it was computed from the previous state.

Speculative batching pays off when a chain rejects several proposals before accepting one. The
runner can resolve those self-loops concurrently rather than draw and reject their trees one at a
time. If the acceptance rate is high, more of the speculative tail will be discarded and the
benefit will be smaller.

Determinism depends on keeping proposal order separate from completion order. Each proposal receives
a random stream derived from the top-level seed and its logical position in the batch, not from
whichever Rayon thread executes it. Work stealing may change when a proposal finishes, but it
cannot change which random values the proposal receives or where its result appears in the batch.
The runner should create a private Rayon pool with `num_workers` threads rather than depend on the
process-global pool.

Scanning the parent graph for every attempt would surrender much of the benefit of parallelism, so
`ReversiblePartitionIndex` may retain district membership and classify each parent edge once. The
index is rebuilt after an accepted transition, when the assignment changes, but not after a
self-loop. It remains a derived index over the authoritative rustworkx/Petgraph graph; it is not a
second representation of the topology. Every parent edge must appear in exactly one classification
bucket.

The Python iterator yields the existing `Partition` for each rejection that precedes the accepted
proposal. It materializes a new child only when the coordinator reaches that acceptance, and it
never materializes the discarded tail. Old parent links are cleared in the same manner as
`MarkovChain`. A fixed seed, worker count, and batch size must reproduce the trajectory. Changing
the worker count or batch size may change it.

The coordinator should return an owned chain result rather than hide this state inside the Python
iterator. That result contains the initial dense assignment, total position count, accepted
transitions as `(position, RecomAssignmentDelta)` records, warning count, exact derived seed, and
resolved worker and batch configuration. Gaps between accepted positions represent self-loops, so
the result does not need one record per yielded position. The Python iterator retains or borrows
the result while it materializes partitions; a later BENDL recorder may read the same log without
consuming it. This ownership is part of the runner contract and must be implemented before the
recording work in `../native-bendl-recording.md` begins.

## Implementation checkpoints

1. Add validated dense-part, part-pair, assignment, ReCom configuration, and outcome types.
2. Implement sparse candidate-pair sequencing and merged-subgraph construction.
3. Implement standard ReCom as one Python-free search plus a PyO3 adapter.
4. Activate each built-in standard variant only when its complete prerequisite route is active.
5. Add multi-member feasible intervals and unequal-target error parity.
6. Add reversible fixtures, then implement reversible proposal and acceptance behavior.
7. Add reusable workspace storage only after a fresh-buffer implementation is correct and has an
   end-to-end baseline.
8. Add the parallel runner, owned chain result, index, and coordinator as an independently reviewed
   checkpoint.

## Verification

### Correctness and compatibility

- Flip validity and population invariants against Python on matched inputs.
- Pair sequence ordering, shuffle semantics, cut-edge weighting, and advance-on-reselect behavior.
- Complete MST/UST prerequisite routing and whole-operation callback fallback.
- Exactly one eight-draw seed across pair selection, trees, cuts, and retries.
- Region-aware, mixed-label, warning, retry, infeasibility, and `MetagraphError` behavior.
- Node holes, tuple and string labels, and partitions with many singleton districts.
- Workspace dirty-versus-fresh same-seed equivalence while alternating merged-graph sizes, MST and
  UST calls, and zero, one, and several region columns.
- Parallel exact-position counts, deterministic fixed-configuration transitions, balance,
  connectivity, self-loop accounting, warning counts, and error propagation. Repeated runs should
  remain identical when task scheduling is deliberately perturbed.
- The owned chain result reconstructs every position from its initial assignment and accepted
  transition log, remains available after the Python iterator is created, and records the resolved
  seed and parallel configuration exactly.

### Performance checks

Use the `compare` command in `benchmarks/benchmark_recom.py` for standard ReCom. Add end-to-end
reversible and parallel modes to that program before activating those checkpoints. Follow the master
benchmark procedure and compare accepted-transition counts or assignment digests so that faster
execution cannot hide changed work.

Use profiling and `micro` only to explain an end-to-end result or guide implementation. If Python
materialization accounts for a small fraction of runtime, optimize the Rust search before broadening
the parallel runner to general `MarkovChain`. Add allocation reuse or indexing one change at a time;
remove it when the end-to-end effect is neutral or negative.

## Exit criteria

Each activated dispatch path defaults to Rust and passes correctness, reproducibility, packaging,
and paired end-to-end performance review. Inactive prerequisites and custom configurations remain
complete Python operations. Parallel reversible ReCom becomes active only with explicit worker and
batch configuration. The initial runner does not support Python callbacks; that limitation belongs
to this checkpoint rather than to the eventual `MarkovChain` design.
