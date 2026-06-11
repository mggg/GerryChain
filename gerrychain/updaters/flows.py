"""Incremental "flow"-based updaters for partitions produced by a Markov chain.

GerryChain explores district plans with a Markov chain meaning each step starts from the current
``Partition`` and produces a child ``Partition`` that differs from it by only a handful of node
reassignments ("flips"). Most quantities we track about a partition (cut edges, perimeters,
boundary nodes, tallies, ...) are exposed as *updater* - functions ``updater(partition)`` whose
results are computed on demand and cached on the partition (see ``Partition.__getitem__``).

Since ReCom steps only modify two districts at a time, for many updaters (e.g. total population),
it is possible to compute the new value for the child partition by starting from the parent's
value and adjusting it using only the nodes that changed assignment. For example, if you know the
population of each part in the parent partition, and you know which nodes joined and left each part,
you can compute the new population of each part by adding the population of the nodes that joined
and subtracting the population of the nodes that left. This is much faster than looping through
all the nodes in the changed parts and summing their populations from scratch. The list of
nodes that joined and left each part is what we call the "flow" of nodes into and out of each part,
and the machinery for computing and responding to that flow is what this module provides.


There are two notions of "flow":

* **Node flow** (:func:`flows_from_changes`): for each part, the set of nodes that joined it
  (``"in"``) and the set that left it (``"out"``) relative to the parent partition. This is exposed
  as ``partition.flows``.
* **Cut-edge flow** (:func:`compute_edge_flows`): for each part, the cut edges that became - or
  stopped being - incident to that part. This is exposed as ``partition.edge_flows``.

Two decorators turn an incremental update rule into a full updater:

* :func:`on_flow` drives an updater from node flow.
* :func:`on_edge_flow` drives an updater from cut-edge flow.

In both cases you supply two pieces:

* an **initializer**, which computes the whole ``{part: value}`` dictionary from scratch. It is used
  for the *root* partition of a chain (the one whose ``partition.parent is None``), where there is
  no parent to diff against.
* an **update rule** (the decorated function), which is called once per changed part on every
  later step and returns the new value for that part, given the parent's value for that part plus
  the in/out flow for that part.

So the lifecycle of a flow-based updater is: compute everything once at the root via the
initializer, then on each subsequent step copy the parent's result and patch only the parts that
actually changed. This is what the docstrings below mean by "initialize" (root) vs. the incremental
"post-initialization" update (every later step).
"""

from __future__ import annotations

import collections
import functools
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..partition.partition import Partition


@functools.lru_cache(maxsize=2)
def neighbor_flips(partition: Partition) -> set[tuple[int, int]]:
    """Return set of edges that were flipped in the given partition compared to its parent.

    Args:
        partition (Partition): A partition of a Graph

    Returns:
        Set[Tuple]: The set of edges that were flipped in the given partition.
    """
    return {
        tuple(sorted((node, neighbor)))
        for node in partition.flips
        for neighbor in partition.graph.neighbors(node)
    }


def create_flow() -> dict[str, set]:
    return {"in": set(), "out": set()}


@functools.lru_cache(maxsize=2)
def flows_from_changes(
    old_partition: Partition, new_partition: Partition
) -> dict[int, dict[str, set[int]]]:
    """Return per-part node flow updates between two partitions.

    Args:
        old_partition (Partition): A partition of a Graph
            representing the previous step.
        new_partition (Partition): A partition of a Graph
            representing the current step.

    Returns:
        Dict: A dictionary mapping each node that changed assignment between the previous and
            current partitions to a dictionary of the form `{'in': <set of nodes that flowed in>,
            'out': <set of nodes that flowed out>}`.
    """

    # frm: TODO: Code: ???:  Grok why there is a test for:  source != target
    #
    # It would seem to me that it would be a logic bug if there
    # was a "flip" that did not in fact change the partition mapping...
    #

    flows = collections.defaultdict(create_flow)
    for node, target in new_partition.flips.items():
        source = old_partition.assignment.mapping[node]
        if source != target:
            flows[target]["in"].add(node)
            flows[source]["out"].add(node)
    return flows


def on_flow(initializer: Callable, alias: str) -> Callable:
    """A decorator that responds to flows of nodes between parts of the partition.

    Use this decorator to create an updater that responds to flows of nodes between parts of the
    partition.

    Decorate a function that takes:
        - The partition
        - The previous value of the updater on a fixed part P_i
        - The new nodes that are just joining P_i at this step
        - The old nodes that are just leaving P_i at this step

    and returns:
        - The new value of the updater for the fixed part P_i.

    This will create an updater whose values are dictionaries of the form `{part: <value of the
    given function on the part>}`.

    The initializer, by contrast, should take the entire partition and return the entire `{part:
    <value>}` dictionary.

    How it works (initialize vs. incremental update):
        The updater this decorator produces behaves differently depending on whether the partition
        is the root of the chain or a later step:

        * **Initialize (root partition).** When ``partition.parent is None`` there is no previous
          step to diff against, so the updater simply calls ``initializer(partition)`` and returns
          the whole ``{part: value}`` dictionary computed from scratch.
        * **Incremental update (every later step).** Otherwise the updater takes the parent's
          cached ``{part: value}`` dictionary (``partition.parent[alias]``), copies it, and then -
          for each part that had any node flow this step - replaces that part's entry with the
          result of calling the decorated function with ``(partition, previous_value_for_part,
          flow["in"], flow["out"])``. Parts with no flow keep the parent's value unchanged, so only
          the handful of parts touched by this step's flips are recomputed.

        This is why the decorated function only needs to describe how a *single* part's value
        changes given the nodes flowing in and out of it, while the initializer must be able to
        compute every part's value directly.

    Note:
        The ``alias`` must match the name the updater is registered under on the partition, because
        the incremental path looks the parent's value up via ``partition.parent[alias]``.

    Example:

    .. code-block:: python

        @on_flow(initializer, alias='my_updater')
        def my_updater(partition, previous, new_nodes, old_nodes):
            # return new value for the part

    Args:
        initializer (Callable): A function that takes the partition and returns a dictionary of the
            form `{part: <value>}`. Used to compute the value from scratch for the root partition.
        alias (str): The name of the updater to be created (and the key it is registered under).

    Returns:
        Callable: A decorator that takes a single-part update function as input and returns a full
        updater function ``updater(partition)``.
    """

    def decorator(function: Callable[..., object]) -> Callable:
        @functools.wraps(function)
        def wrapped(partition: Partition, previous: dict | None = None) -> dict:
            if partition.parent is None:
                return initializer(partition)

            if previous is None:
                previous = partition.parent[alias]

            new_values = previous.copy()

            for part, flow in partition.flows.items():
                new_values[part] = function(partition, previous[part], flow["in"], flow["out"])

            return new_values

        return wrapped

    return decorator


def compute_edge_flows(partition: Partition) -> dict[int, dict[str, set[tuple[int, int]]]]:
    """Computes the flow of cut edges between a partition and its parent.

    Args:
        partition (Partition): A partition of a Graph

    Returns:
        Dict: A flow dictionary containing the flow from the parent of this partition to this
            partition. This dictionary is of the form `{part: {'in': <set of edges that flowed in>,
            'out': <set of edges that flowed out>}}`.
    """
    edge_flows = collections.defaultdict(create_flow)
    assignment = partition.assignment
    old_assignment = partition.parent.assignment

    for node, neighbor in neighbor_flips(partition):
        edge = (node, neighbor)

        old_source = old_assignment.mapping[node]
        old_target = old_assignment.mapping[neighbor]

        new_source = assignment.mapping[node]
        new_target = assignment.mapping[neighbor]

        # frm:  Clarification to myself...
        #       A "cut edge" is one where the nodes in the edge are assigned to different
        #       districts.  So, how does a flip change whether an edge is a cut edge?  There
        #       are three possibilities: 1) the edge goes from not being a cut edge to being
        #       a cut edge, 2) the edge goes from being a cut edge to not being a cut edge,
        #       and 3) the edge was a cut edge before and is still a cut edge after the flip,
        #       but the partition assignments to one or the other nodes in the edge changes.
        #
        #       That is what the if-stmt below is doing - determining which of the three
        #       cases each flip falls into.  It updates the flows accordingly...
        #
        cut = new_source != new_target  # after flip, the edge is a cut edge
        was_cut = old_source != old_target  # before flip, the edge was a cut edge

        if not cut and was_cut:
            # was a cut edge before, but now is not, so flows out of both
            edge_flows[old_target]["out"].add(edge)
            edge_flows[old_source]["out"].add(edge)
        elif cut and not was_cut:
            # was not a cut edge before, but now is, so flows into both
            edge_flows[new_target]["in"].add(edge)
            edge_flows[new_source]["in"].add(edge)
        elif cut and was_cut:
            # If an edge was cut and still is cut, we need to make sure the
            # edge is listed under the correct parts.
            # frm: Clarification to myself...  Python set subtraction will delete
            #       from the set on the left any members of the set on the right,
            #       so no_longer_incident_parts will determine if either old_target,
            #       or old_source has changed - that is, whether the assignment of
            #       the one of the old mappings has changed - if so, the edge has
            #       gone "out" of that partition.  If you do the subtraction the
            #       other way, you find whether the new mappings have changed
            #       and you can then update the "in" flows
            #
            no_longer_incident_parts = {old_target, old_source} - {
                new_target,
                new_source,
            }
            for part in no_longer_incident_parts:
                edge_flows[part]["out"].add(edge)

            newly_incident_parts = {new_target, new_source} - {old_target, old_source}
            for part in newly_incident_parts:
                edge_flows[part]["in"].add(edge)

    return edge_flows


def on_edge_flow(initializer: Callable, alias: str) -> Callable:
    """A decorator that responds to flows of cut edges between parts of the partition.

    Use this decorator to create an updater that responds to flows of cut edges between parts of
    the partition.

    Decorate a function that takes:
        - The partition
        - The previous value of the updater for a fixed part P_i
        - The new cut edges that are just joining P_i at this step
        - The old cut edges that are just leaving P_i at this step

    and returns:
        - The new value of the updater for the fixed part P_i.

    This will create an updater whose values are dictionaries of the form `{part: <value of the
    given function on the part>}`.

    The initializer, by contrast, should take the entire partition and return the entire `{part:
    <value>}` dictionary.

    How it works (initialize vs. incremental update):
        This is the cut-edge analogue of :func:`on_flow`; the only difference is that it is driven
        by ``partition.edge_flows`` (cut edges joining/leaving each part) instead of
        ``partition.flows`` (nodes joining/leaving each part).

        * **Initialize (root partition).** When the partition has no parent, the updater calls
          ``initializer(partition)`` and returns the whole ``{part: value}`` dictionary computed
          from scratch.
        * **Incremental update (every later step).** Otherwise it copies the parent's cached
          ``{part: value}`` dictionary and, for each part with cut-edge flow this step, replaces
          that part's entry with the result of calling the decorated function with
          ``(partition, previous_value_for_part, new_edges=flow["in"], old_edges=flow["out"])``.

    Note:
        The ``alias`` must match the name the updater is registered under, because the incremental
        path looks the parent's value up via ``partition.parent[alias]``.

    Example:

    .. code-block:: python

        @on_edge_flow(initializer, alias='my_updater')
        def my_updater(partition, previous, new_edges, old_edges):
            # return new value of the part

    Args:
        initializer (Callable): A function that takes the partition and returns a dictionary of the
            form `{part: <value>}`. Used to compute the value from scratch for the root partition.
        alias (str): The name of the updater to be created (and the key it is registered under).

    Returns:
        Callable: A decorator that takes a single-part update function as input and returns a full
        updater function ``updater(partition)``.
    """

    def decorator(f: Callable[..., object]) -> Callable:
        @functools.wraps(f)
        def wrapper(partition: Partition) -> dict:
            if not partition.parent:
                return initializer(partition)
            edge_flows = partition.edge_flows
            previous = partition.parent[alias]

            new_values = previous.copy()
            for part in partition.edge_flows:
                new_values[part] = f(
                    partition,
                    previous[part],
                    new_edges=edge_flows[part]["in"],
                    old_edges=edge_flows[part]["out"],
                )
            return new_values

        return wrapper

    return decorator
