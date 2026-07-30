"""Compatibility helpers for APIs deprecated after GerryChain 0.3.2.

The adapters in this module keep legacy handling outside the canonical implementations and
signatures. Every compatibility path emits a :class:`DeprecationWarning` that identifies the
replacement API and its planned removal in GerryChain 2.0.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import random
import warnings
from collections.abc import Callable, Collection, Mapping
from typing import Any, ParamSpec, TypeVar, cast

P = ParamSpec("P")
R = TypeVar("R")


def _warn(message: str, stacklevel: int = 3) -> None:
    """Emit a deprecation warning attributed to the compatibility helper's caller.

    Args:
        message (str): Warning text shown to the user.
        stacklevel (int, optional): Number of stack frames for :func:`warnings.warn` to skip when
            reporting the warning location. Defaults to 3.
    """
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)


def deprecated_parameters(
    renamed: Mapping[str, str] | None = None,
    ignored: Mapping[str, str] | None = None,
    defaults: Mapping[str, Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Translate legacy keywords before calling a function with its canonical signature.

    Renamed arguments are translated to their canonical names, ignored arguments are removed, and
    legacy defaults are supplied when their canonical argument is absent. Each compatibility
    action emits a :class:`DeprecationWarning`. The decorated callable retains the wrapped
    function's metadata and canonical signature.

    Args:
        renamed (Mapping[str, str] | None, optional): Mapping from legacy keyword names to
            canonical keyword names.
        ignored (Mapping[str, str] | None, optional): Mapping from removed keyword names to the
            explanation appended to their warning. Supplied values are discarded.
        defaults (Mapping[str, Any] | None, optional): Mapping from canonical keyword names to
            legacy default values. A default is supplied only when the argument was not otherwise
            bound.

    Returns:
        Callable[[Callable[P, R]], Callable[P, R]]: A decorator that adds the requested legacy
            argument handling.

    Raises:
        TypeError: When a caller supplies both a legacy keyword and its canonical replacement.
    """
    renamed = {} if renamed is None else renamed
    ignored = {} if ignored is None else ignored
    defaults = {} if defaults is None else defaults

    def decorate(fn: Callable[P, R]) -> Callable[P, R]:
        signature = inspect.signature(fn)
        fn_name = getattr(fn, "__qualname__", type(fn).__qualname__)

        @functools.wraps(fn)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            mutable_kwargs = cast(dict[str, Any], kwargs)
            for old_name, new_name in renamed.items():
                if old_name not in mutable_kwargs:
                    continue
                if new_name in mutable_kwargs:
                    raise TypeError(
                        f"{fn_name} received both {old_name!r} and {new_name!r}; "
                        f"use only {new_name!r}."
                    )
                mutable_kwargs[new_name] = mutable_kwargs.pop(old_name)
                _warn(
                    f"{fn_name}(..., {old_name}=...) is deprecated; use "
                    f"{new_name}=... instead. The legacy name will be removed in GerryChain 2.0."
                )

            for name, reason in ignored.items():
                if name not in mutable_kwargs:
                    continue
                mutable_kwargs.pop(name)
                _warn(
                    f"{fn_name}(..., {name}=...) is deprecated and ignored. {reason} "
                    "The argument will be rejected in GerryChain 2.0."
                )

            if defaults:
                bound = signature.bind_partial(*args, **mutable_kwargs)
                for name, value in defaults.items():
                    if name in bound.arguments:
                        continue
                    mutable_kwargs[name] = value
                    _warn(
                        f"{fn_name}() omitted {name!r}; using the legacy default {value!r}. "
                        f"Pass {name}=... explicitly. The implicit default will be removed in "
                        "GerryChain 2.0."
                    )

            return fn(*args, **mutable_kwargs)

        return wrapped

    return decorate


def adapt_legacy_callable(
    fn: Callable[..., R],
    role: str,
    renamed: Mapping[str, str] | None = None,
    dropped: Collection[str] = (),
) -> Callable[..., R]:
    """Adapt an old callback to current keyword names and the keyword-only ``rng`` protocol.

    The returned wrapper removes an unsupported ``rng`` keyword, translates current keyword names
    back to names declared by the legacy callback, and drops selected unsupported keywords. A
    warning is emitted when the adapter is created, not on every callback invocation. Callbacks
    that already satisfy the protocol are returned unchanged.

    Args:
        fn (Callable[..., R]): Callback to inspect and, if necessary, wrap.
        role (str): Human-readable callback role used in the warning message.
        renamed (Mapping[str, str] | None, optional): Mapping from current keyword names to their
            pre-1.0 names.
        dropped (Collection[str], optional): Current keyword names to omit when the callback does
            not accept them.

    Returns:
        Callable[..., R]: The original callback when it is compatible or cannot be inspected;
            otherwise, a metadata-preserving compatibility wrapper.

    Note:
        Exceptions raised by the callback propagate directly. The adapter never retries a call.
    """
    if getattr(fn, "__gerrychain_legacy_adapter__", False):
        return fn

    try:
        parameters = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return fn

    accepts_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )
    accepts_rng = accepts_kwargs or (
        "rng" in parameters and parameters["rng"].kind is not inspect.Parameter.POSITIONAL_ONLY
    )
    reverse_renames = {
        current: legacy
        for current, legacy in ({} if renamed is None else renamed).items()
        if not accepts_kwargs and current not in parameters and legacy in parameters
    }
    dropped_parameters = {name for name in dropped if not accepts_kwargs and name not in parameters}
    if accepts_rng and not reverse_renames and not dropped_parameters:
        return fn

    changes = [f"{current!r} as {legacy!r}" for current, legacy in reverse_renames.items()]
    changes.extend(f"without {name!r}" for name in dropped_parameters)
    if not accepts_rng:
        changes.append("without the keyword-only 'rng' parameter")
    _warn(
        f"{role} {getattr(fn, '__name__', type(fn).__name__)!r} uses the pre-1.0 callback "
        f"signature ({', '.join(changes)}). Update it for the 1.0 callback protocol; legacy "
        "callbacks will stop working in GerryChain 2.0.",
        stacklevel=4,
    )

    @functools.wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> R:
        if not accepts_rng:
            kwargs.pop("rng", None)
        for name in dropped_parameters:
            kwargs.pop(name, None)
        for current, legacy in reverse_renames.items():
            if current in kwargs:
                kwargs[legacy] = kwargs.pop(current)
        return fn(*args, **kwargs)

    cast(Any, wrapped).__gerrychain_legacy_adapter__ = True
    return wrapped


def adapt_legacy_cut_choice(fn: Callable[..., R]) -> Callable[..., R]:
    """Adapt both legacy cut-choice signatures without changing the tree implementation.

    The three-argument legacy form accepted ``populated_graph``, ``region_surcharge``, and
    ``cut_edge_list`` positionally. Its wrapper accepts the current form, where
    ``cut_edge_list`` is positional and the remaining inputs, including ``rng``, are keyword-only.
    Other callback shapes are handled by :func:`adapt_legacy_callable`.

    Args:
        fn (Callable[..., R]): Cut-choice callback to inspect and, if necessary, wrap.

    Returns:
        Callable[..., R]: A callback compatible with the current cut-choice protocol.
    """
    try:
        parameters = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return fn

    names = list(parameters)
    if names[:3] != ["populated_graph", "region_surcharge", "cut_edge_list"] or "rng" in parameters:
        return adapt_legacy_callable(fn, "Cut-choice function")

    _warn(
        f"Cut-choice function {getattr(fn, '__name__', type(fn).__name__)!r} uses the pre-1.0 "
        "(populated_graph, region_surcharge, cut_edge_list) signature. Put cut_edge_list first and "
        "accept populated_graph, region_surcharge, and rng by keyword; the legacy signature will "
        "stop working in GerryChain 2.0.",
        stacklevel=4,
    )

    @functools.wraps(fn)
    def wrapped(
        cut_edge_list: Any,
        /,
        *,
        populated_graph: Any,
        region_surcharge: Any,
        rng: Any,
    ) -> R:
        return fn(populated_graph, region_surcharge, cut_edge_list)

    cast(Any, wrapped).__gerrychain_legacy_adapter__ = True
    return wrapped


def deprecated_alias(
    old_name: str,
    new_name: str,
    fn: Callable[P, R],
) -> Callable[P, R]:
    """Return a warning wrapper for a renamed public callable.

    Args:
        old_name (str): Fully qualified legacy name shown in warnings and exposed as the wrapper's
            name.
        new_name (str): Fully qualified replacement name shown in warnings.
        fn (Callable[P, R]): Canonical callable to invoke.

    Returns:
        Callable[P, R]: A metadata-preserving wrapper that warns on every call before forwarding
            all arguments to ``fn``.
    """

    @functools.wraps(fn)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        _warn(
            f"{old_name} is deprecated; use {new_name} instead. The legacy name will be removed "
            "in GerryChain 2.0."
        )
        return fn(*args, **kwargs)

    wrapped.__name__ = old_name.rsplit(".", 1)[-1]
    wrapped.__qualname__ = wrapped.__name__
    return wrapped


def allow_legacy_missing_rng(fn: Callable[P, R]) -> Callable[P, R]:
    """Allow a direct pre-1.0 call that omits the now-required ``rng`` keyword.

    Calls that omit ``rng`` receive a new, independently seeded :class:`random.Random` instance
    and emit a :class:`DeprecationWarning`. Calls that supply ``rng`` pass through unchanged.

    Args:
        fn (Callable[P, R]): Callable whose current protocol requires keyword-only ``rng``.

    Returns:
        Callable[P, R]: A metadata-preserving wrapper that supplies ``rng`` when necessary.
    """
    fn_name = getattr(fn, "__qualname__", type(fn).__qualname__)

    @functools.wraps(fn)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        mutable_kwargs = cast(dict[str, Any], kwargs)
        if "rng" not in mutable_kwargs:
            mutable_kwargs["rng"] = random.Random()
            _warn(
                f"{fn_name}() now requires the keyword-only 'rng' argument. Omitting it "
                "is deprecated and will fail in GerryChain 2.0."
            )
        return fn(*args, **mutable_kwargs)

    return wrapped


def deprecated_property(old_name: str, new_name: str, *, writable: bool = False) -> property:
    """Return a property forwarding a deprecated attribute name to its replacement.

    Reading the property warns and returns the canonical attribute. When ``writable`` is true,
    assignment also warns and delegates to the canonical attribute so its setter and validation
    behavior remain in effect.

    Args:
        old_name (str): Fully qualified legacy attribute name shown in warnings.
        new_name (str): Replacement attribute name on the same instance.
        writable (bool, optional): Whether the deprecated property should forward assignments.
            Defaults to ``False``.

    Returns:
        property: A deprecated forwarding property.
    """

    def warn() -> None:
        _warn(
            f"{old_name} is deprecated; use {new_name} instead. The legacy name will be removed "
            "in GerryChain 2.0.",
            stacklevel=4,
        )

    def get(instance: object) -> Any:
        warn()
        return getattr(instance, new_name)

    if not writable:
        return property(get)

    def set_(instance: object, value: Any) -> None:
        warn()
        setattr(instance, new_name, value)

    return property(get, set_)


def deprecated_lazy_alias(
    old_name: str,
    new_name: str,
    module_name: str,
    attribute_name: str,
) -> Callable[..., Any]:
    """Return a warning wrapper that resolves a moved callable without creating import cycles.

    Lazy resolution avoids import cycles for public functions that moved between modules.

    Args:
        old_name (str): Fully qualified legacy name shown in warnings and exposed as the wrapper's
            name.
        new_name (str): Fully qualified replacement name shown in warnings.
        module_name (str): Import path containing the replacement callable.
        attribute_name (str): Replacement callable's name within ``module_name``.

    Returns:
        Callable[..., Any]: A wrapper that warns, resolves the replacement, and forwards all
            arguments when invoked.
    """

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        _warn(
            f"{old_name} is deprecated; use {new_name} instead. The legacy import will be removed "
            "in GerryChain 2.0."
        )
        fn = getattr(importlib.import_module(module_name), attribute_name)
        return fn(*args, **kwargs)

    wrapped.__name__ = old_name.rsplit(".", 1)[-1]
    wrapped.__qualname__ = wrapped.__name__
    return wrapped


def legacy_epsilon_tree_bipartition(*args: Any, **kwargs: Any) -> Any:
    """Compatibility entry point for the function moved out of ``gerrychain.tree``.

    Args:
        *args (Any): Positional arguments forwarded to the canonical function.
        **kwargs (Any): Keyword arguments forwarded to the canonical function.

    Returns:
        Any: The canonical function's return value.
    """
    _warn(
        "gerrychain.tree.epsilon_tree_bipartition is deprecated; import it from "
        "gerrychain.proposals.tree_proposals instead. The legacy import will be removed in "
        "GerryChain 2.0."
    )
    from .proposals.tree_proposals import epsilon_tree_bipartition

    return epsilon_tree_bipartition(*args, **kwargs)


def legacy_bipartition_tree_random(*args: Any, **kwargs: Any) -> Any:
    """Compatibility wrapper for the renamed random bipartition function.

    The canonical function returns ``(num_cuts, nodes)``. This wrapper warns and returns only the
    selected nodes, or ``None`` when no cut was found, matching ``bipartition_tree_random``.

    Args:
        *args (Any): Positional arguments forwarded to
            ``bipartition_tree_random_with_num_cuts``.
        **kwargs (Any): Keyword arguments forwarded to
            ``bipartition_tree_random_with_num_cuts``.

    Returns:
        Any: The selected node set when at least one cut was found; otherwise, ``None``.
    """
    _warn(
        "gerrychain.tree.bipartition_tree_random is deprecated; use "
        "bipartition_tree_random_with_num_cuts instead. The legacy name will be removed in "
        "GerryChain 2.0."
    )
    from .tree.bipartition_tree import bipartition_tree_random_with_num_cuts

    num_cuts, nodes = bipartition_tree_random_with_num_cuts(*args, **kwargs)
    return nodes if num_cuts else None


def legacy_predecessors(graph: Any, root: Any) -> dict[Any, Any]:
    """Compatibility wrapper for ``Graph.predecessors``.

    Args:
        graph (Any): Graph providing a ``predecessors`` method.
        root (Any): Root node passed to that method.

    Returns:
        dict[Any, Any]: Mapping from each reached node to its predecessor.
    """
    _warn(
        "gerrychain.tree.predecessors is deprecated; use graph.predecessors instead. The legacy "
        "function will be removed in GerryChain 2.0."
    )
    return graph.predecessors(root)


def legacy_successors(graph: Any, root: Any) -> dict[Any, list[Any]]:
    """Compatibility wrapper for ``Graph.successors``.

    Args:
        graph (Any): Graph providing a ``successors`` method.
        root (Any): Root node passed to that method.

    Returns:
        dict[Any, list[Any]]: Mapping from each reached node to its successor nodes.
    """
    _warn(
        "gerrychain.tree.successors is deprecated; use graph.successors instead. The legacy "
        "function will be removed in GerryChain 2.0."
    )
    return graph.successors(root)


def legacy_flips(partition: Any) -> Any:
    """Compatibility updater returning ``Partition.flips``.

    Args:
        partition (Any): Partition whose flips should be returned.

    Returns:
        Any: The partition's flips mapping, or ``None`` when it has no flips.
    """
    _warn(
        "gerrychain.updaters.flips is deprecated; use partition.flips directly. The legacy "
        "updater will be removed in GerryChain 2.0."
    )
    return partition.flips


def legacy_give_constant_attribute(graph: Any, attribute: Any, value: Any) -> None:
    """Compatibility wrapper for the removed grid helper.

    This preserves the removed ``gerrychain.grid.give_constant_attribute`` helper while directing
    callers to mutate node data explicitly.

    Args:
        graph (Any): Graph exposing ``node_indices`` and mutable ``node_data`` mappings.
        attribute (Any): Node attribute key to set.
        value (Any): Value assigned to every node.
    """
    _warn(
        "gerrychain.grid.give_constant_attribute is deprecated; set node data directly instead. "
        "The helper will be removed in GerryChain 2.0."
    )
    for node in graph.node_indices:
        graph.node_data(node)[attribute] = value
