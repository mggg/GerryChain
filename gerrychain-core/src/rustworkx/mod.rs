//! Rustworkx-derived binding code. Placeholder: registers nothing until the vendored
//! rustworkx 0.18.1 binding sources land here with their provenance record (UPSTREAM.md).

use pyo3::prelude::*;

pub(crate) fn register(_module: &Bound<'_, PyModule>) -> PyResult<()> {
    Ok(())
}
