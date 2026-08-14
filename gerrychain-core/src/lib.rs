//! Composition point for the single GerryChain extension module.
//!
//! `src/rustworkx/` holds only rustworkx-derived binding code (a vendored port of the upstream
//! 0.18.1 bindings); `src/gerrychain/` holds original GerryChain implementations. The
//! rustworkx-derived module must not depend on the GerryChain-specific module.

use pyo3::prelude::*;

mod gerrychain;
mod rustworkx;

// The Python module is named "rustworkx" (imported as gerrychain.rustworkx.rustworkx); the
// Rust function is named differently only to avoid shadowing `mod rustworkx` above.
#[pymodule(name = "rustworkx")]
fn rustworkx_extension(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    rustworkx::register(py, module)?;
    gerrychain::register(module)?;
    Ok(())
}
