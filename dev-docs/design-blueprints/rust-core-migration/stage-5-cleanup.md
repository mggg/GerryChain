# Stage 5: final 1.x deprecations and the 2.0 interface

## Goal

The final stage is reserved for public-interface cleanup. The backing-graph switch, interface-type
change, and external dependency removal are already present in the baseline; they do not belong in
the algorithm ports.

Once the active Rust checkpoints have demonstrated compatibility and acceptable benchmark results,
we can decide which 1.x compatibility mechanisms remain part of GerryChain and which disappear at
the 2.0 boundary. Public decisions must precede cleanup. Code does not become dispensable merely
because the Rust implementation no longer calls it.

## Constraints inherited from the baseline

Nothing in the algorithm migration authorizes us to remove the public compatibility mechanisms that
remain supported through 1.x. `gerrychain.rustworkx` must continue to provide its 0.18.1 interface,
NX-backed graphs must retain complete Python operations, and custom callbacks must continue to work
through fallback. GerryChain-specific extension functions remain private under `_gerrychain`.

The backing-graph switch and removal of the external rustworkx dependency are already complete in
the baseline, so this stage should not reopen either migration incidentally. Any decision to narrow
`gerrychain.rustworkx`, remove a callback path, or make NetworkX ingestion-only belongs to the 2.0
interface work described below.

## Relationship to RustReCom

None.

## Design decisions and tradeoffs

- Support the complete `gerrychain.rustworkx` compatibility namespace through 1.x, keeping the graph
  migration mechanical. GerryChain accepts the associated compatibility and security maintenance
  until 2.0.
- Narrow that namespace only through explicit 2.0 decisions. The maintenance surface becomes
  smaller, while affected users receive a documented replacement for each removed import or graph
  operation.
- Decide separately whether NetworkX remains a backing or becomes ingestion-only. Persistent
  backing preserves existing behavior. Converting at ingestion simplifies dispatch and internal
  state, but makes conversion timing and object identity more visible.
- Document the 2.0 replacement for a callback or fallback before removing it. The simpler dispatch
  is not worth an unexplained public migration.
- Retain `rustworkx-core` unless ownership or benchmark results justify replacement. Folding it into
  GerryChain would increase source and security maintenance without making the algorithms faster by
  itself.
- Preserve the validated Rust type model during cleanup. Having fewer callers does not make raw
  integers or coordinated booleans safer.

## Proposed implementation

### Final 1.x releases

The remaining 1.x releases should clarify the 2.0 boundary rather than remove compatibility code
prematurely. Before either interface disappears, users should be able to distinguish a temporary
compatibility surface from the GerryChain-specific interface that will replace it.

1. Restate that `gerrychain.rustworkx` is a transitional compatibility namespace: its complete
   0.18.1 surface is supported throughout 1.x but not promised in 2.0.
2. Document the 2.0 replacement for each public use of `gerrychain.rustworkx`; prefer
   GerryChain-specific graph APIs over another complete rustworkx facade.
3. Deprecate the 1.x callback adapters and fallbacks that 2.0 will replace.

### 2.0 release

Public API changes belong at the 2.0 boundary and require documented replacements. We are trying to
reduce permanent maintenance, not to make the Rust implementation smaller at the expense of an
unexplained migration.

1. Remove 1.x callback adapters and fallbacks only where the 2.0 interface explicitly replaces
   them.
2. Decide whether NetworkX remains a persistent `Graph` backing or becomes an ingestion-only
   format converted at construction (the `networkx` dependency stays either way).
3. Narrow or remove the public `gerrychain.rustworkx` surface. Keep only the bindings supported by
   the 2.0 graph interface; move implementation-only bindings behind a private namespace.
4. Prune derived Rust internals unreachable from the 2.0 public surface. Narrowing the public
   surface is a documented 2.0 break decided case by case, not an assumed cleanup.
5. Consider folding or replacing `rustworkx-core` only if the dependency becomes an
   actual maintenance or performance problem.
6. Update documentation, type stubs, migration guidance, and wheel smoke tests. Regenerate the
   Cargo license inventory with `tools/generate_cargo_notices.py` and verify the SBOM.

## Implementation checkpoints

1. Inventory every Python fallback, callback adapter, compatibility export, and deprecated entry
   point with its current callers and tests.
2. Classify each item as retained public behavior, replaced behavior with a documented migration,
   or implementation-only code unreachable from the public interface.
3. Land deprecations and migration documentation before removal.
4. Remove one class of compatibility code at a time and run the complete routing, typing, pickle,
   wheel, and namespace-isolation suites.
5. Use compiler reachability, `rg`, and coverage from representative chains to identify Rust code
   made unreachable by the public decision.
6. Prune types and modules only after their callers disappear. Do not collapse validated domain
   types back to raw integers merely because fewer call sites remain.
7. Record each 2.0 public-interface decision and any deviation from this blueprint in an ADR.

## Verification

### Correctness and compatibility

- The wheel continues to contain one shared library.
- No compatibility import reintroduces the external `rustworkx` runtime dependency.
- Public graph and assignment labels remain Python values; dense identifiers remain private.
- Removing a Python fallback does not silently remove callback exception or RNG behavior from an
  otherwise retained interface.
- Pruning scratch workspaces does not replace Petgraph with custom topology storage.
- Accepted input cannot trigger a Rust panic after compatibility branches disappear.

### Performance checks

Before removing a compatibility path, use the `compare` command in
`benchmarks/benchmark_recom.py` against the final 1.x and proposed 2.0 artifacts. Follow the master
benchmark procedure. Cleanup is acceptable when the end-to-end results show no material regression,
or when an explicit public simplification justifies the measured cost. Use `micro` only to diagnose
a regression.

## Exit criteria

The wheel still contains one compiled shared library; every retained graph entry point is an
explicit part of the 2.0 interface; the migration guide names every removed or changed public
contract; and unreachable Python and Rust compatibility code has been removed without weakening
the validated type model.
