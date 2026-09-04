# Stage 1: spanning-tree checkpoints

## Goal

We begin by formalizing the graph topology that GerryChain supports. Both spanning-tree algorithms
assume a simple, undirected graph, although the baseline constructors enforce only the second
condition. Once that discrepancy has been resolved, `random_spanning_tree` and
`uniform_spanning_tree` can move into Rust as separate checkpoints. Later work may depend on one
tree family before the other is ready; neither port requires a change to the public Python
signature or result shape.

## Constraints inherited from the baseline

The Rust tree functions will sit behind the existing Python wrappers, so their results must remain
interchangeable with trees produced by the Python path. In particular, the returned graph must
preserve rustworkx node indices, including holes; reuse the original Python node payloads; and carry
the edge attributes expected by later GerryChain functions.

The baseline `random_spanning_tree` writes a `random_weight` to every edge of the input graph, even
though only the weights on the returned tree are used by later cut selection. We will remove that
side effect from both backends. The input graph remains unchanged, while each edge in the returned
random spanning tree still carries the weight used to select it. Region surcharges, including their
treatment of unassigned values and multiple attributes, must modify those weights according to the
same rules as the Python implementation. Removing the mutation is an intentional 1.x change and
requires a focused test and changelog entry.

`uniform_spanning_tree` continues to accept `region_surcharge=None` and an empty mapping, while a
nonempty mapping raises the existing `ValueError`. NX-backed graphs remain on the Python path. The
topology, unhashable-region, and disconnected-input corrections specified below are deliberate 1.x
changes rather than parity requirements.

## Relationship to RustReCom

RustReCom constructs spanning trees in Rust and uses them only within ReCom. It never has to convert
those trees into public graph objects with GerryChain's Python labels and payloads. We will take the
same approach when a Rust algorithm consumes the tree directly, while the public tree functions
will continue to return rustworkx-compatible graphs.

We will not adopt RustReCom's custom graph storage. Rustworkx and Petgraph remain authoritative;
the reusable workspaces introduced in later stages will hold only temporary algorithm state.

## Design decisions and tradeoffs

- Use one dense graph snapshot per operation so every algorithm handles rustworkx index holes and
  canonical ordering in the same way. Retained partition state may later share that snapshot across
  calls.
- Extract populations and region attributes before releasing the GIL. Standalone calls still pay
  for one extraction pass, but their algorithm loops contain no Python object access.
- Require region identifiers to be hashable. This intentionally removes accidental 1.x support for
  unhashable values and permits ordinary dictionary lookup during region classification.
- Stop writing `random_weight` to the input graph on both backends. The returned random spanning
  tree still carries the weights needed by balanced-cut selection, but the source graph no longer
  accumulates hidden state from a sampling operation.
- Derive one Rust RNG from the caller's Python RNG. Retries and helper calls can then remain in
  Rust, although seeded trajectories will not match the Python implementation draw for draw.
- Rely on Petgraph for sampled trees and union-find rather than maintaining another graph library.
  The public path will still pay to construct the Python-visible `PyGraph` result.
- Preserve `random_weight` on public tree edges; GerryChain's balanced-cut functions read it. A
  ReCom operation that remains in Rust may keep the same value directly on the Petgraph edge and
  avoid constructing a Python attribute dictionary.
- Leave NX-backed graphs on Python, preserving the current path without introducing an implicit
  graph conversion. The initial acceleration will consequently apply only to RX-backed graphs.

Here, "dense" means contiguous and without index holes. The snapshot is a temporary Rust structure
that maps sparse rustworkx indices into the contiguous range used by Petgraph algorithms. A dense
snapshot should pay significant dividends in the hot loops because populations, parent links,
degrees, region identifiers, and traversal state can all be stored in compact vectors and accessed
directly by node index. We pay the sparse-to-dense translation cost once when constructing the
snapshot rather than performing a hash lookup or checking for an index hole at every step of the
algorithm. This representation should also improve cache locality and make the data structures used
by Petgraph and union-find more natural.

## Proposed implementation

### Graph topology validation

GerryChain's algorithms were originally defined for simple, undirected graphs. The baseline
constructors reject directed graphs, but they admit self-loops and parallel edges despite the
assumptions made by the algorithms that consume them. We will close that gap before activating
either tree checkpoint: `Graph.from_networkx()` and `Graph.from_rustworkx()` will reject self-loops
and parallel edges by default, while directed graphs will remain unconditionally invalid.

Because this deliberately restricts the 1.x interface, we will retain a narrow compatibility path.
A caller may pass `allow_unsupported_topology=True` to construct a graph that contains a self-loop
or parallel edge. The option waives those two checks; it does not define the behavior of later
GerryChain algorithms. The resulting `Graph` must retain the option when it is wrapped, converted,
or used to construct a subgraph so that an accepted graph is not rejected at a later construction
boundary.

Validation concerns the graph's contents rather than the capabilities of its container. A
rustworkx `PyGraph`, for example, may permit parallel edges without containing any. We will reject
it only when the edge list contains a self-loop or repeats an unordered pair of endpoints. NetworkX
and rustworkx inputs must be judged by the same rule.

### Rust module layout

Shared graph, attribute, and RNG infrastructure will live beside the tree implementations in
GerryChain's private Rust module. Keeping our code visibly separate from the copied rustworkx source
also leaves the ownership boundary legible without tracing imports through the binding layer.

```text
gerrychain-core/src/gerrychain/
├── mod.rs          # register(): adds the _gerrychain submodule (exists; grows entries)
├── python_rng.rs   # Python-draw conversion and ChaCha8 initialization
├── node_attributes.rs
├── dense_graph_snapshot.rs
└── tree/
    ├── mod.rs
    ├── random_spanning_tree.rs
    └── uniform_spanning_tree.rs
```

These Rust functions will be registered under the private `_gerrychain` submodule, not among the
copied rustworkx names. The Python wrappers remain the public API, so the Rust modules can change
without creating another supported extension namespace.

### Shared infrastructure

#### RNG conversion (`python_rng.rs`)

We will use `ChaCha8Rng` as the Rust pseudorandom number generator. Unlike `StdRng`, it identifies
the RNG algorithm explicitly; it is also fast enough for these operations and accepts a reproducible
256-bit seed.

The caller-owned Python RNG remains the source of truth. Users continue to seed and manage the
Python RNG, and the PyO3 entry point derives the Rust seed only after dispatch and deterministic
validation:

1. Call the caller-owned Python RNG's `random()` method exactly eight times.
2. Require each result to be finite and in `[0, 1)`.
3. Convert each result `x` to `floor(x * 2^32)` as a `u32`.
4. Concatenate the eight words in little-endian order and initialize one `ChaCha8Rng`.

Keep the numeric conversion Python-free so it can be tested with a fixed eight-value vector. It may
return `[u8; 32]` or construct the Rust RNG directly; a named seed wrapper is unnecessary unless the
implementation finds another invariant for it to enforce.

Pass the same mutable Rust RNG through every stochastic helper. No helper constructs or seeds
another RNG. Together with stable candidate ordering, this preserves deterministic trajectories for
a fixed Python seed and GerryChain version.

#### Dense graph snapshot (`dense_graph_snapshot.rs`)

Rustworkx indices are stable but may contain holes, whereas the Petgraph algorithms we intend to use
work most naturally with contiguous indices. Each standalone Rust call will therefore build a
`DenseGraphSnapshot`. It owns the mappings, edge order, adjacency, and extracted payload tables
needed by the operation; the shipped graph remains the authoritative topology.

The snapshot needs a stable mapping in both directions, adjacency in dense-node order, and source
edge records in rustworkx order. The reverse mapping must represent index holes explicitly. We will
keep node indices, edge indices, and neighbor rows in ascending order; sampled iteration must not
depend on hash-map order.

Use Petgraph's natural index type or another index that can represent every live node. A narrower
integer representation is acceptable only with a checked conversion at snapshot construction. The
constructor must return an error rather than truncate an accepted rustworkx index.

I would probably use a representation similar to the following:

```rust
struct DenseGraphEdge {
    first_dense_node_index: usize,
    second_dense_node_index: usize,
    rustworkx_edge_index: usize,
}

pub(crate) struct DenseGraphSnapshot {
    rustworkx_node_index_by_dense_index: Vec<usize>,
    dense_node_index_by_rustworkx_index: Vec<Option<usize>>,
    neighbor_dense_indices_by_node: Vec<Vec<usize>>,
    edges_in_rustworkx_order: Vec<DenseGraphEdge>,
}
```

The field names may change, but the two mappings are indispensable. Every dense node needs one
stable route back to its public rustworkx index, and every live rustworkx node needs one route into
the compact arrays used by the algorithms.

#### Node-attribute extraction (`node_attributes.rs`)

Repeated Python attribute access would require the GIL inside the tree and cut loops. Populations
and region values will therefore be extracted into dense Rust arrays before the GIL is released, at
the cost of one Python traversal per operation.

One helper extracts a named numeric attribute in dense-node order. A second assigns equal region
values the same dense class while preserving `None` as an unassigned value. Their relationship to
the graph snapshot will look roughly like this:

```rust
pub(crate) fn extract_numeric_node_attribute(
    py: Python<'_>,
    graph: &PyGraph,
    graph_snapshot: &DenseGraphSnapshot,
    attribute_name: &str,
) -> PyResult<Vec<f64>>;

pub(crate) fn classify_node_attribute_values(
    py: Python<'_>,
    graph: &PyGraph,
    graph_snapshot: &DenseGraphSnapshot,
    attribute_name: &str,
) -> PyResult<Vec<Option<usize>>>;
```

Region attributes serve as categorical identifiers, and the Rust path needs to assign a stable
integer class to each distinct value. We will therefore require every non-null value associated
with a key in `region_surcharge` to be hashable. The baseline accepts some unhashable values only
because it compares them for equality; we will not preserve that accidental permissiveness.

We should validate hashability in the public Python path before backend dispatch and before
consuming any random draws, and apply the same validation to NX- and RX-backed graphs. The PyO3
adapter can then assign equal values the same dense region index with dictionary lookup, and the
Python-free Rust algorithm compares only those integer indices.

The inner graph is `crate::rustworkx::graph::PyGraph { pub graph: StablePyGraph<Undirected>, .. }`.
Its fields are already public, so we do not need to change the vendored source.

#### Tree states (`tree/mod.rs`)

Kruskal and Wilson construct acyclic edge sets before we know that they span the graph. Kruskal may
also produce a final forest for a disconnected input, matching the behavior of the standalone
Python function. We will represent this not-yet-validated construction state as `SpanningForest`
and promote it to `SpanningTree` only after validating that it spans every live node and is
connected. Balanced-cut functions accept only `SpanningTree`, so they cannot accidentally operate
on a disconnected result.

```rust
struct SpanningTreeEdge {
    random_weight: Option<f64>,
}

struct SpanningForest {
    graph: petgraph::graph::UnGraph<(), SpanningTreeEdge>,
}

struct SpanningTree {
    graph: petgraph::graph::UnGraph<(), SpanningTreeEdge>,
}
```

A private checked conversion should prove the node count, acyclicity, and connected spanning-tree
invariant before promoting `SpanningForest` to `SpanningTree`. Balanced-cut functions accept only
`&SpanningTree`. A random tree edge stores its sampled weight, while a uniform tree edge leaves the
field empty and receives a fallback weight only if cut selection asks for one.

### Random spanning tree

We need to preserve the following behavior from `spanning_tree.py`:

1. One weight per edge, iterated in canonical edge order: `stream.random::<f64>()`.
2. Surcharges: for each attribute in `region_surcharge`, add the surcharge to edges whose
   endpoints do not share the same non-null class (via `classify_node_attribute_values`), honoring
   `treat_unassigned_as_single_region` (a shared "unassigned" class when set). Match the
   multi-attribute combination rules in the Python body exactly.
3. Run Kruskal directly over the extracted edge records using Petgraph's `UnionFind`. This keeps
   weighted selection outside Python and lets the selected Petgraph edge retain its sampled weight.
   Sort by `(weight, source_edge_index)` so equal floating-point weights produce a deterministic
   tree.
4. Returned edges carry `{"random_weight": w}` payload dicts. The balanced-cut finders use this
   value to weight cut candidates, and the default cut choice selects the maximum weight. Node
   payloads are shared `Py<PyAny>` clones. Node indices equal the input's live indices: insert
   `rustworkx_node_index_by_dense_index` in ascending order and preserve holes with the existing
   throwaway-and-remove pattern.
5. Leave the input graph unchanged.
6. Return a shipped `PyGraph` pyclass; the Python wrapper finishes with the existing
   `Graph.from_rustworkx()` call so ID-map behavior stays in Python.

The existing Python wrapper is sufficient for dispatch. Common validation comes first, after which
the wrapper inspects the graph backing. An RX-backed call passes the shipped `PyGraph`, normalized
arguments, and caller-owned RNG to the private PyO3 entry point; an NX-backed call continues through
the existing Python body. Because the function accepts no custom callables, the backing is the only
dispatch condition. That decision must precede Rust seed derivation so that the Python path does not
advance the caller's RNG merely by declining to use Rust.

### Uniform spanning tree

The uniform path uses Wilson's algorithm, matching the Python baseline without enumerating spanning
trees. Sorted adjacency rows make neighbor selection independent of hash-table iteration order.

The root should be drawn via `stream.random_range(0..n_live)` over the canonical node order,
followed by loop-erased random walks over the sorted adjacency rows
(`neighbor_dense_indices_by_node[row][stream.random_range(0..degree)]`). Result construction and
dispatch match the random-tree checkpoint, except that the edges receive empty `{}` payloads. This
is consistent with the current uniform tree, which records no weights; Stage 2 describes the cut
finders' fallback-draw path. The existing `region_surcharge` behavior also remains intact: `None`
and an empty mapping are accepted, while a nonempty mapping raises `ValueError`.

Since connectivity does not depend on the random seed, the common Python path should check it
before choosing an implementation or consuming any random draws. The baseline already raises
`IndexError("Cannot choose from an empty sequence")` when a disconnected graph contains an isolated
node, while a disconnected component without an isolate may walk forever because it can never
reach the sampled root. The port regularizes those cases by raising the same exception for every
disconnected input, regardless of the graph backing. This intentional 1.x correction also means
that an invalid call no longer advances the Python RNG. The same rule applies to direct
bipartition paths that require a spanning tree and belongs in the changelog.

## Implementation checkpoints

1. Add graph topology validation, the explicit bypass, propagation through graph wrappers and
   conversions, and consistent NX/RX tests.
2. Add the pure Python-draw-to-seed conversion, its fixed-vector tests, and the PyO3 adapter that
   consumes exactly eight Python draws after dispatch.
3. Add `DenseGraphSnapshot` and attribute extraction with node holes, stable edge ordering, missing
   columns, null regions, and unhashable-region rejection covered.
4. Add `SpanningTreeEdge`, `SpanningForest`, and checked conversion to `SpanningTree` using Petgraph
   and its union-find implementation.
5. Implement and activate random spanning trees, including node payload cloning and
   `random_weight` materialization on the result without mutating the input graph.
6. Implement and activate Wilson uniform spanning trees, including disconnected-input behavior.
7. Run differential, routing, reproducibility, and artifact checks before activating either public
   dispatch path.

## Verification

### Correctness and compatibility

- Fixed seed-vector test: `random.Random(K)` produces a recorded 32-byte seed; a Rust call
  advances the supplied RNG by exactly eight `random()` calls.
- An NX-backed fallback does not consume the eight draws used to seed a Rust operation; it advances
  the Python RNG only as required by the existing Python algorithm.
- `Graph` always rejects directed graphs. It rejects self-loops and parallel edges consistently for
  NX- and RX-backed inputs unless the caller sets `allow_unsupported_topology=True`. Tests for the
  bypass may allow an algorithm to reject the graph, but it must do so without a Rust panic. A
  multigraph-capable container with no parallel edges remains valid.
- Unhashable region values raise `TypeError` before random draws on both NX- and RX-backed graphs.
- A disconnected uniform-tree call raises the baseline's `IndexError` before consuming random
  draws, irrespective of its backing or whether the graph contains an isolate.
- Invariants vs Python on shared connected fixtures: `n - 1` edges, connectivity, acyclicity, node
  IDs preserved (subgraph inputs included), node payload identity shared, `random_weight` present
  on every random-spanning-tree edge, the input edge payloads unchanged, and high region surcharges
  keeping small regions whole (distributional, seeded).
- On disconnected input, the random-spanning-tree path returns the same spanning forest as the
  Python baseline; the uniform path follows the rejection rule above.
- Seeded repeatability and `PYTHONHASHSEED` independence in subprocesses.
- Golden trajectory update + changelog entry in the same change as each default switch.

### Performance checks

Neither tree checkpoint adds a separate microbenchmark gate. Use `micro` while developing the tree
algorithms or diagnosing a later end-to-end regression. Once an active ReCom route depends on a
tree checkpoint, assess its effect through the end-to-end comparison in the master benchmark
procedure.

## Exit criteria

The topology checkpoint is complete when both graph backings reject unsupported topologies by
default and preserve the documented bypass through wrapping, conversion, and subgraph construction.
Each tree checkpoint is complete when its built-in RX-backed path uses Rust by default, the existing
public tests and new differential tests pass, and the resulting trajectory change is reviewed and
documented in the same change. Once a supported chain route depends on a tree checkpoint, that
route must also pass the master end-to-end benchmark gate.
