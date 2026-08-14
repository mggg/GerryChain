"""Placeholder for the shipped rustworkx port.

This stub will be replaced by the vendored upstream rustworkx 0.18.1 package facade. Until
then only the private native smoke-test hook exists here, and GerryChain itself does not
import this package.
"""

from gerrychain.rustworkx.rustworkx import _gerrychain

__all__ = ["_gerrychain"]
