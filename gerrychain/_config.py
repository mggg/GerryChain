"""Runtime configuration for GerryChain.

This module controls *optional* integrity checks that are off by default for performance, but can
be turned on while debugging (for example in a Jupyter notebook) or in the test suite.

Two kinds of validation exist in GerryChain:

* **Always-on structural invariants** - cheap, O(1) checks (such as "a Graph has exactly one
  embedded backing graph") that run unconditionally at construction boundaries. These cost nothing
  measurable and need no configuration.

* **Opt-in thorough audits** - more expensive, O(nodes + edges) checks (such as "every node carries
  a dict data payload") that are wasteful to run during a long chain. These are gated behind the
  runtime-checks switch below.

Modelled after ``numpy.seterr`` / ``numpy.errstate`` and ``torch.autograd.set_detect_anomaly`` - a
global switch with a context manager, defaulting to off, that a user (read: maintainer) flips on
when something looks wrong.

Example::

    import gerrychain

    # Turn thorough validation on globally (e.g. while debugging a notebook):
    gerrychain.set_runtime_checks(True)

    # ...or just for a block:
    with gerrychain.runtime_checks():
        partition = Partition(graph, assignment, updaters)
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator

# Off by default: long chain runs should not pay for thorough validation.
_RUNTIME_CHECKS_ENABLED = False


def set_runtime_checks(enabled: bool) -> None:
    """Enable or disable GerryChain's optional thorough integrity checks.

    These checks are OFF by default because they add O(nodes + edges) overhead at graph-construction
    boundaries, which is wasteful during long chain runs. Turn them on while debugging if you
    suspect a malformed or corrupted graph::

        import gerrychain
        gerrychain.set_runtime_checks(True)

    They are also enabled automatically throughout the GerryChain test suite.

    Args:
        enabled (bool): ``True`` to enable thorough checks, ``False`` to disable.
    """
    global _RUNTIME_CHECKS_ENABLED
    _RUNTIME_CHECKS_ENABLED = bool(enabled)


def runtime_checks_enabled() -> bool:
    """Return ``True`` if optional thorough integrity checks are currently enabled."""
    return _RUNTIME_CHECKS_ENABLED


@contextlib.contextmanager
def runtime_checks(enabled: bool = True) -> Iterator[None]:
    """Context manager that toggles thorough integrity checks within a block.

    The previous setting is restored on exit (including if an exception is raised)::

        with gerrychain.runtime_checks():
            partition = Partition(graph, assignment, updaters)

    Args:
        enabled (bool, optional): The setting to apply inside the block. Defaults to
            ``True``.
    """
    global _RUNTIME_CHECKS_ENABLED
    previous = _RUNTIME_CHECKS_ENABLED
    _RUNTIME_CHECKS_ENABLED = bool(enabled)
    try:
        yield
    finally:
        _RUNTIME_CHECKS_ENABLED = previous
