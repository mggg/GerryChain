# Vendored rustworkx provenance

This directory, the `gerrychain/rustworkx/` Python package, and the `tests/rustworkx_compat/`
suite are a vendored copy of rustworkx, imported and adapted by GerryChain. This file is the
canonical record of what was copied and every way the copy differs from upstream.

## Upstream revision

- Project: rustworkx (<https://github.com/Qiskit/rustworkx>), Apache-2.0 (see
  `LICENSE.rustworkx` at the repository root).
- Version: **0.18.1**
- Commit: **`736a1bc382ef15a4c864b068d433436fb6dfaf5d`** (the `0.18.1` tag)
- Imported: 2026-08-14
- Source verification: the PyPI sdist `rustworkx-0.18.1.tar.gz` (sha256
  `30affe6ee52a6257a01152418f9c1686ca114e7ab4a3bf87bb87fe35b7350f3e`) is byte-identical to the
  tag for `src/`, `rustworkx/`, `Cargo.lock`, `pyproject.toml`, and `setup.py`.

## Path mapping

| Upstream                     | Here                                   |
| ---------------------------- | -------------------------------------- |
| `src/*.rs` (binding crate)   | `gerrychain-core/src/rustworkx/`       |
| `src/lib.rs`                 | `gerrychain-core/src/rustworkx/mod.rs` |
| `rustworkx/` (Python facade) | `gerrychain/rustworkx/`                |
| `tests/`                     | `tests/rustworkx_compat/`              |
| `LICENSE`                    | `LICENSE.rustworkx` (repository root)  |

## Changes from upstream

Every modified file carries a top-of-file notice pointing here. Here is the complete list of changes
made so far (nearly all of them are import or path adjustments):

1. **Rust module nesting**: `crate::` paths became `crate::rustworkx::` (and `$crate::`
   likewise inside macros) because the bindings compile as a submodule of `gerrychain-core`
   rather than a crate root.
2. **Registration**: `src/lib.rs` became `mod.rs`; its `#[pymodule] fn rustworkx` became
   `pub(crate) fn register(...)`, called from `gerrychain-core/src/lib.rs`, which owns the one
   `#[pymodule]` for the whole extension.
3. **Compatibility version**: `__version__` is the literal `"0.18.1"` instead of
   `env!("CARGO_PKG_VERSION")`, which would otherwise report gerrychain-core's crate version.
4. **Python module paths**: `#[pyclass(module = "rustworkx...")]` attributes,
   `create_exception!(rustworkx, ...)` and `import_exception!(rustworkx.visit, ...)`
   declarations, facade absolute imports, and `sys.modules` strings all moved from
   `rustworkx...` to `gerrychain.rustworkx...`.
5. **Pest grammar path**: `#[grammar = "dot_parser/dot.pest"]` became
   `"rustworkx/dot_parser/dot.pest"` (paths are relative to the crate's `src/`).
6. **Formatting**: one `use` statement lengthened by the path nesting was reflowed by rustfmt
   (`shortest_path/mod.rs`).
7. **Cargo packaging**: workspace dependency versions were inlined; the `rustworkx-core` path
   dependency became the exact registry dependency `=0.18.1`; PyO3's `abi3-py310` became
   `abi3-py311` (GerryChain's floor is 3.11); `extension-module` moved behind a cargo feature
   so `cargo test` links libpython. `Cargo.lock` pins pyo3 0.29.0 to match upstream's lockfile
   resolution (pyo3 0.29.2 resolves hashbrown 0.17, which the vendored conversions do not
   compile against).
8. **Inherited tests**: import statements updated mechanically to `gerrychain.rustworkx`; no
   assertions were changed. One test is skipped outright:
   `visualization/test_graphviz.py::TestGraphvizDraw::test_method` carries a
   `@unittest.skip` because its unseeded random graph intermittently crashes broken local
   graphviz `sfdp` builds (see Known deviations). Remove the skip to restore upstream
   coverage on machines with a working sfdp.

## Known deviations

- `tests/rustworkx_compat/visualization/test_graphviz.py::TestGraphvizDraw::test_method` is
  skipped (change 8 above), so this copy runs one fewer test than upstream. The underlying
  cause is environmental, not a defect of this copy: the test draws an unseeded random graph,
  which intermittently crashes broken local graphviz `sfdp` builds, and the identical call
  fails identically through the upstream-published rustworkx wheels on such machines.

## Auditing this copy

Compare against the recorded revision with:

```sh
curl -sL https://github.com/Qiskit/rustworkx/archive/736a1bc382ef15a4c864b068d433436fb6dfaf5d.tar.gz | tar xz
diff -r rustworkx-736a1bc382ef15a4c864b068d433436fb6dfaf5d/src gerrychain-core/src/rustworkx
diff -r rustworkx-736a1bc382ef15a4c864b068d433436fb6dfaf5d/rustworkx gerrychain/rustworkx
diff -r rustworkx-736a1bc382ef15a4c864b068d433436fb6dfaf5d/tests tests/rustworkx_compat
```

The diff must contain only the changes enumerated above plus the per-file notices. Do not add
GerryChain algorithms to any vendored directory; original code belongs in
`gerrychain-core/src/gerrychain/` and the ordinary `gerrychain/` packages.
