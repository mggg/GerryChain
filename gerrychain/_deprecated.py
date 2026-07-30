"""Compatibility helpers for APIs deprecated after GerryChain 0.3.2."""

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
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)


def deprecated_parameters(
    renamed: Mapping[str, str] | None = None,
    ignored: Mapping[str, str] | None = None,
    defaults: Mapping[str, Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Translate legacy keywords before calling a function with its canonical signature."""
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
    """Adapt an old callback to current keyword names and the keyword-only ``rng`` protocol."""
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
    """Adapt both legacy cut-choice signatures without changing the tree implementation."""
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
    """Return a warning wrapper for a renamed public callable."""

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
    """Allow a direct pre-1.0 call that omits the now-required ``rng`` keyword."""
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


def deprecated_property(old_name: str, new_name: str) -> property:
    """Return a property forwarding a deprecated attribute name to its replacement."""

    def get(instance: object) -> Any:
        _warn(
            f"{old_name} is deprecated; use {new_name} instead. The legacy name will be removed "
            "in GerryChain 2.0."
        )
        return getattr(instance, new_name)

    return property(get)


def deprecated_lazy_alias(
    old_name: str,
    new_name: str,
    module_name: str,
    attribute_name: str,
) -> Callable[..., Any]:
    """Return a warning wrapper that resolves a moved callable without creating import cycles."""

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
    """Compatibility entry point for the function moved out of ``gerrychain.tree``."""
    _warn(
        "gerrychain.tree.epsilon_tree_bipartition is deprecated; import it from "
        "gerrychain.proposals.tree_proposals instead. The legacy import will be removed in "
        "GerryChain 2.0."
    )
    from .proposals.tree_proposals import epsilon_tree_bipartition

    return epsilon_tree_bipartition(*args, **kwargs)


def legacy_bipartition_tree_random(*args: Any, **kwargs: Any) -> Any:
    """Compatibility wrapper for the renamed random bipartition function."""
    _warn(
        "gerrychain.tree.bipartition_tree_random is deprecated; use "
        "bipartition_tree_random_with_num_cuts instead. The legacy name will be removed in "
        "GerryChain 2.0."
    )
    from .tree.bipartition_tree import bipartition_tree_random_with_num_cuts

    num_cuts, nodes = bipartition_tree_random_with_num_cuts(*args, **kwargs)
    return nodes if num_cuts else None


def legacy_predecessors(graph: Any, root: Any) -> dict[Any, Any]:
    """Compatibility wrapper for ``Graph.predecessors``."""
    _warn(
        "gerrychain.tree.predecessors is deprecated; use graph.predecessors instead. The legacy "
        "function will be removed in GerryChain 2.0."
    )
    return graph.predecessors(root)


def legacy_successors(graph: Any, root: Any) -> dict[Any, list[Any]]:
    """Compatibility wrapper for ``Graph.successors``."""
    _warn(
        "gerrychain.tree.successors is deprecated; use graph.successors instead. The legacy "
        "function will be removed in GerryChain 2.0."
    )
    return graph.successors(root)


def legacy_flips(partition: Any) -> Any:
    """Compatibility updater returning ``Partition.flips``."""
    _warn(
        "gerrychain.updaters.flips is deprecated; use partition.flips directly. The legacy "
        "updater will be removed in GerryChain 2.0."
    )
    return partition.flips


def legacy_give_constant_attribute(graph: Any, attribute: Any, value: Any) -> None:
    """Compatibility wrapper for the removed grid helper."""
    _warn(
        "gerrychain.grid.give_constant_attribute is deprecated; set node data directly instead. "
        "The helper will be removed in GerryChain 2.0."
    )
    for node in graph.node_indices:
        graph.node_data(node)[attribute] = value
