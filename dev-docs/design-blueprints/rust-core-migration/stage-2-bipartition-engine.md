# Stage 2: balanced cuts, bipartition, recursive partitioning

## Goal

The balanced-cut and bipartition engine forms the first checkpoint. Recursive partitioning and
random assignment follow as a second checkpoint that depends on it. Together, they move tree
rooting, population accumulation, balanced-cut discovery, cut selection, retry control, and
recursive assignment into complete Rust operations. Otherwise, each tree or eligible cut would
send the retry loop back across the Python boundary.

## Constraints inherited from the baseline

The Rust cut engine must identify the same population-balanced cuts as the Python implementation.
Balance uses the inclusive test `abs(pop - ideal) <= epsilon * ideal`, so a population exactly on
the tolerance boundary qualifies. In two-sided mode, both components created by removing the tree
edge must balance. In one-sided mode, either component may be returned when it satisfies the target.
The representation of `_PopulatedGraph`, its degree bookkeeping, and its temporary subsets do not
need to survive the port.

A cut ordinarily takes its weight from `random_weight` on the corresponding tree edge. If no weight
is present, both implementations will draw one from their current RNG. The baseline also draws and
discards a value when the edge already has a weight; we will remove that unnecessary work from the
Python path and the Rust port. Seeded trajectories will change, but the proposal distribution will
not since the discarded value never influences which cut is selected.

Region-aware selection narrows the field before comparing those weights. With one to three region
attributes, `_region_preferred_max_weight_choice` first asks whether any cut crosses all of the
configured boundaries. If not, it works through smaller combinations, considering more attributes
before fewer and using total surcharge to order combinations of the same size. Once it reaches a
combination represented among the eligible cuts, it returns the cut with the greatest weight in
that group. With four or more region attributes, it skips the combinatorial search and simply takes
the greatest-weight cut from the full list.

Tree reuse will depend on the cut finder. Memoization examines every edge in one pass, whereas
contraction may expose another cut when a new root changes the contraction order, so we will update
the Rust retry policy to search a memoized tree exactly once and a contraction tree
`node_repeats + 1` times.

The current baseline warns that `node_repeats` does not help with memoization but performs the extra
searches anyway, which is a waste. So, we will change that behavior in 1.x: memoization will
ignore a positive `node_repeats` value on both backends, and the warning will be updated to say
that the value is ignored and that positive values apply only to contraction and custom cut
finders. This change, like the removal of the discarded weight draw, will require focused tests, a
golden update, and a changelog entry.

Apart from those two deliberate changes, retry behavior remains part of the contract. Reaching
`warn_attempts` emits `BipartitionWarning` unless pair reselection is enabled. Exhausting
`max_attempts` raises `ReselectException` when the caller has permitted another district pair and
`RuntimeError` otherwise. Caller-provided trees and custom tree, root, cut-finder, or cut-choice
functions must continue through the complete Python path.

## Relationship to RustReCom

Little applies here. RustReCom demonstrates reusable split buffers and tree-based population
searches, but its ordinary random-MST variants, retry rules, and self-loop rules all differ from
GerryChain's. We will preserve the existing behavior rather than adopt RustReCom's for now.

## Design decisions and tradeoffs

- Represent each population-balanced cut by the tree edge to remove and by whether the returned
  node set is the child subtree or its complement. The Python node set is constructed only after a
  cut has been selected. Eligible-cut order remains significant because it affects weighting and
  seeded selection.
- Use union-find to accumulate contraction subsets instead of repeatedly unioning sets. The lower
  allocation cost comes with a requirement to test isolates and root selection explicitly.
- Keep user-supplied tolerances distinct from derived feasible population intervals. Rules intended
  for user targets must not reject a valid derived interval such as `[0, 0]`; the PyO3 entry point
  will perform the necessary conversion.
- Represent retry, warning, reselection, and infeasibility as Rust outcomes so that the control flow
  can be tested without Python exceptions. The PyO3 adapter remains responsible for emitting the
  same warning or exception as the Python path, at the same point in the operation.
- Route custom tree, root, cut-finder, and cut-choice callables through the complete Python path.
  Those configurations remain unaccelerated so that customization and Python RNG ownership retain
  their current behavior.
- Apply the Stage 1 connectivity rule before either backend is selected. A path that requires a
  spanning tree rejects disconnected input before consuming random draws; the Rust and Python
  paths must not expose different contracts.

## Proposed implementation

### Domain types

Population tolerance and a derived feasible interval are mathematically related, but they are not
interchangeable. The same is true of cut-selection modes and the several values that govern retry
behavior, so we should represent these distinctions with validated types rather than coordinated
floats, strings, and booleans. Past the PyO3 boundary, the search then receives a configuration
whose invariants have already been established.

The code below describes the normalized configuration passed to Rust; it does not mirror the public
signature. Python dispatch has already selected a supported built-in path by the time these values
are constructed.

```rust
struct PopulationTargetTolerance { target_population: f64, relative_tolerance: f64 }
struct FeasiblePopulationRange { inclusive_lower: f64, inclusive_upper: f64 }
enum PopulationBalanceMode { OneSide, BothSides }
enum BalancedCutAlgorithm { SubtreeMemoization, LeafContraction }
enum BalancedCutSelection { MaximumWeight, PreferRegionBoundaries }
struct BipartitionRetryPolicy {
    searches_per_tree: NonZeroUsize,
    maximum_tree_attempts: NonZeroUsize,
    warning_attempt_threshold: usize,
    reselect_pair_on_exhaustion: bool,
}
```

`PopulationTargetTolerance` validates the target and epsilon supplied by the caller, whereas
`FeasiblePopulationRange` represents the inclusive bounds derived from them and may include zero.
The three enums record independent choices about balance, cut discovery, and cut selection without
asking the search to interpret strings, booleans, or Python callable identities.

`searches_per_tree` is not intended as a public setting or a direct alias for `node_repeats`.
Instead, it records the tree-reuse cadence after we account for the selected cut finder: memoization
produces one search per tree, while contraction produces `node_repeats + 1`. Keeping that resolved
value in `BipartitionRetryPolicy` means the retry driver does not need to branch on the cut
algorithm merely to decide when it should draw a new tree. The two `NonZeroUsize` fields also rule
out retry policies that cannot execute even once.

The Python interface is more permissive than this internal policy. Zero or negative values that the
baseline accepts must continue through the Python path until we either define an equivalent Rust
outcome or reject them uniformly before backend dispatch. I would vote to reject the negative
values.

Do not construct a validated population or retry value with `expect` from accepted Python input.
The PyO3 adapter maps validation failures to the baseline's Python exceptions before deriving the
Rust seed.

### Balanced cuts and bipartition

#### Rust layout and data structures

Rooted-tree state, balanced-cut discovery, and retry orchestration obey different invariants. They
should therefore be separated and tested independently, even though the public operation runs as
one Rust call.

```text
gerrychain-core/src/gerrychain/tree/
├── rooted_population_tree.rs
├── balanced_cuts.rs    # memoization + contraction finders, cut choice
└── bipartition.rs      # retry driver, warning/exception mapping, num_cuts variant
```

```rust
pub(crate) struct RootedPopulationTree<'a> {
    spanning_tree: &'a SpanningTree,        // this will be borrowed so it needs a lifetime
    population_by_dense_node: &'a [f64],
    parent_by_dense_node: Vec<Option<usize>>,
    parent_edge_weight_by_dense_node: Vec<f64>,
    dense_nodes_in_breadth_first_order: Vec<usize>,
    subtree_population_by_dense_node: Vec<f64>,
    total_population: f64,
    feasible_population_range: FeasiblePopulationRange,
}

impl RootedPopulationTree<'_> {
    fn is_population_feasible(&self, population: f64) -> bool {
        self.feasible_population_range.contains(population)
    }
}

pub(crate) struct BalancedCutCandidate {
    cut_child_dense_node_index: usize,
    cut_edge_weight: f64,
    selected_tree_side: CutSide,
    crossed_region_attribute_indices: Vec<usize>,
}

pub(crate) enum BipartitionExhaustion {
    ReselectPair,
    RaiseRuntimeError,
}

pub(crate) enum BipartitionSearchOutcome {
    CutFound {
        selected_dense_node_indices: Vec<usize>,
        balanced_cut_count: usize,
        bipartition_warning_count: usize,
    },
    SearchExhausted {
        tree_attempts: usize,
        bipartition_warning_count: usize,
        disposition: BipartitionExhaustion,
    },
}
```

Given a validated tree, population array, balance interval, selection mode, and mutable RNG, the
cut search returns either an eligible cut or a typed failure. A later success does not erase
warnings accrued on earlier attempts, and exhaustion must retain whether the caller should reselect
a district pair or raise `RuntimeError`. A direct bipartition search will ordinarily report zero or
one warning; a recursive coordinator may accumulate several. The PyO3 adapter maps this information
to Python labels, warnings, and exceptions. A smaller result type is welcome if it preserves all of
these distinctions.

The principal semantic choice is to preserve GerryChain's cut-selection rule rather than adopt
RustReCom's random choice. GerryChain considers both the weight of the cut edge and the regions
crossed by the cut, a rule that we have found to behave better in practice. Trees constructed in
Rust will carry the cut-selection weight directly on each Petgraph edge. A supported prebuilt
Python tree instead requires one GIL-bound O(V) pass to read its `random_weight` payloads while
constructing `RootedPopulationTree`. Draw a fallback weight only when the edge has no
`random_weight`, and apply the same rule to the Python implementation. This is an intentional 1.x
trajectory change, so it needs a focused RNG test, a golden update, and a changelog entry.

The cut-choice implementation in `balanced_cuts.rs` will provide `max_weight`, with ties resolved
by canonical eligible-cut order, and the region-preferred variant. We will compute the
crossed-region attributes from the Stage 1 region-classification columns for the graph being split.
The power-set preference for one to three attributes and the four-or-more fallback must match
`_region_preferred_max_weight_choice` exactly.

The contraction finder remains available for root-dependent repeated searches and legacy
configurations. A leaf worklist and Petgraph union-find preserve its semantics without repeated
Python set unions:

```rust
pub(crate) struct LeafContractionState {
    remaining_degree_by_dense_node: Vec<usize>,
    component_population_by_dense_node: Vec<f64>,
    merged_components: petgraph::unionfind::UnionFind<usize>,
}
```

#### Retry driver (`bipartition.rs`)

Tree reuse, redraws, warning thresholds, and exhaustion belong in one Python-free Rust driver. A
stochastic retry loop should not cross Python on every attempt, and warning timing is easier to test
when the search returns an outcome rather than raising Python exceptions internally.

The dispatcher derives `BipartitionRetryPolicy.searches_per_tree` from the selected cut finder and
`node_repeats`, following the rule above. The driver owns cut search, tree-attempt counting,
warning-threshold state, and tree redraws. It returns a `BipartitionSearchOutcome`; the PyO3 adapter
emits `BipartitionWarning` and maps exhaustion to the existing `ReselectException` or
`RuntimeError`. A custom `spanning_tree_fn` routes the whole call to Python before the driver runs
or the Rust seed is derived.

`bipartition_tree_random_with_num_cuts` shares the driver and returns `(num_cuts, nodes)`, which
Stage 3's reversible checkpoint consumes.

#### Contraction-specific validation

The contraction cut finder roots the sampled spanning tree and initializes its work queue with
every leaf. Because it later looks up each leaf's parent, the root cannot itself be a leaf. So we
will select the root from nodes whose degree in the sampled tree is greater than one.

The common connectivity validation established in Stage 1 applies here. A direct bipartition call
that requires a spanning tree rejects disconnected input before selecting the backend or consuming
random draws. The Python fallback and Rust path use the same validation.

#### One seed per top-level call

One ChaCha8 stream covers the complete bipartition operation. The Python RNG remains the source of
truth without imposing a Python call on every retry or eligible cut.

`bipartition_tree` threads that stream through root choice, fallback weights, tree redraws, and cut
choice. A dedicated test asserts exactly eight `random()` draws on the caller's RNG per top-level
call regardless of retry count. The reuse-cadence tests pin one memoization search per tree and
`node_repeats + 1` contraction searches, including the handling of a caller-provided first tree.

### Recursive partitioning and random assignment

Rather than make one Python-to-Rust bipartition call per district, we will run the complete
recursive assignment as one Rust operation. We pay for graph extraction once, and population debt,
part targets, and RNG state remain under the same coordinator.

`recursive_tree_part` in `gerrychain/partition/initial_partition_generators.py` and
`Partition.from_random_assignment` carve parts one at a time with `single_district_cut=True` and
the documented per-step targets, then bisect the remainder. One stream spans the complete
recursion. Part labels are caller-supplied hashables; Rust uses dense part indices and maps them
back through a label table. Preserve `PopulationBalanceError`, retry exhaustion, and mixed-label
behavior.

The recursive implementation should be a Python-free function over validated part targets, part
labels represented as dense indices, and one mutable RNG. Its result is either a typed assignment or
a typed failure. Tests must establish that every node is assigned exactly once and that no helper
derives another seed.

## Implementation checkpoints

1. Add and test `PopulationTargetTolerance`, `FeasiblePopulationRange`, balance modes, cut
   selection, and retry policy without PyO3.
2. Build the rooted-tree representation and memoization finder over `SpanningTree`.
3. Add contraction with distinct-neighbor validation and parity fixtures.
4. Add cut selection, region preference, retry cadence, warnings, and typed outcomes.
5. Activate built-in bipartition dispatch only after the full routing table passes.
6. Add pure recursive partitioning and activate random assignment as a separate checkpoint.

Keep the Python callable paths intact. A custom spanning-tree, cut-finder, root-choice, or
cut-choice function routes the entire top-level call to Python, including tree construction.

## Verification

### Correctness and compatibility

- Exact-boundary populations (inclusive epsilon bound, both sides), impossible cuts (infeasible
  epsilon), disconnected graphs, node-ID holes, shrinking subgraphs, retry exhaustion, pair
  reselection, exception and warning propagation, mixed labels.
- Cut-choice parity: fixtures where region-preferred and max-weight choices differ, checked
  against the Python implementation's selection on identical candidate sets.
- Tree-reuse tests cover one search per tree under memoization and `node_repeats + 1` searches under
  contraction. Fallback calls (custom callables and NX-backed graphs) use the Python RNG directly
  and do not consume the eight draws reserved for a Rust operation.
- A positive `node_repeats` with memoization emits the revised warning, performs one search per
  tree, and behaves the same on NX- and RX-backed graphs.
- Weighted cuts do not consume fallback-weight draws; unweighted cuts consume exactly one each on
  both backends.
- Population and connectivity invariants vs Python on generated small graphs; random-assignment
  and hash-seed reproducibility suites against the Rust default.
- Direct Rust entry points reject invalid balance and retry configuration before consuming any
  Python RNG draws; tests use a counting RNG.
- Warning tests cover success after the threshold, direct exhaustion, recursive subcalls, and
  reversible retry behavior rather than only one successful path.

### Performance checks

No separate microbenchmark should gate this stage. `micro` remains appropriate while developing the
balanced-cut search or diagnosing a later end-to-end regression. Once an active ReCom route depends
on the bipartition checkpoint, assess its effect through the end-to-end comparison in the master
benchmark procedure.

## Exit criteria

Each completed checkpoint uses Rust by default for its built-in RX-backed path. Public callable
customization continues to use the Python fallback. Population and connectivity invariants match
Python on generated small graphs, and each default switch includes its golden updates and changelog
entry.
