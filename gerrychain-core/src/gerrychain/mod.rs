//! Original GerryChain implementations and their PyO3 bindings. Native names stay private:
//! everything registers under the `_gerrychain` submodule, never among the copied public
//! rustworkx names.

use pyo3::prelude::*;

/// Smoke-test hook: proves the native module built, loaded, and can be called.
#[pyfunction]
fn native_ping() -> &'static str {
    "gerrychain-core"
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    let private = PyModule::new(module.py(), "_gerrychain")?;
    private.add_function(wrap_pyfunction!(native_ping, &private)?)?;
    module.add_submodule(&private)?;
    Ok(())
}
