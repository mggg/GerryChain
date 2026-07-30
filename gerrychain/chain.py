"""
This module provides the MarkovChain class, which is designed to facilitate the creation
and iteration of Markov chains in the context of political redistricting and gerrymandering
analysis. It allows for the exploration of different districting plans based on specified
constraints and acceptance criteria.

Key Components:

- MarkovChain: The main class used for creating and iterating over Markov chain states.
- Validator: A helper class for validating proposed states in the Markov chain. See
  Validator for more details.


Usage:
The primary use of this module is to create an instance of MarkovChain with appropriate
parameters like proposal function, constraints, acceptance function, and initial state,
and then to iterate through the states of the Markov chain, yielding a new proposal
at each step. The chain can be configured all at once in the constructor or incrementally
by attribute assignment; see the MarkovChain docstring.

Dependencies:

- typing: Used for type hints.

Last Updated: 14 Jul 2026
"""

from __future__ import annotations

import random
import numpy
from collections.abc import Callable, Iterable, Iterator
from typing import Any, cast

from gerrychain._deprecated import adapt_legacy_callable, deprecated_parameters
from gerrychain._rng import make_rng
from gerrychain.accept import AcceptanceFn, always_accept
from gerrychain.constraints import ConstraintFn, Validator
from gerrychain.partition import Partition
from gerrychain.proposals import ProposalFn


class MarkovChain:
    """
    MarkovChain is a class that creates an iterator for iterating over the states
    of a Markov chain run in a gerrymandering analysis context.

    It allows for the generation of a sequence of partitions (states) of a political
    districting plan, where each partition represents a possible state in the Markov chain.

    Example usage:

    .. code-block:: python

        chain = MarkovChain(proposal_fn, constraints, acceptance_fn, initial_partition, total_steps)
        for state in chain:
            # Do whatever you want - print output, compute scores, ...

    The chain may also be configured incrementally. Any parameter omitted from the constructor can
    be assigned afterward, and the configuration is checked when iteration begins (or explicitly,
    via :meth:`check_valid`):

    .. code-block:: python

        chain = MarkovChain(total_steps=1000)
        chain.initial_partition = Partition(graph, assignment, updaters)
        chain.proposal_fn = ReCom.cut_edges_mst(pop_col="TOTPOP", pop_target=ideal, epsilon=0.01)
        chain.constraints = [contiguous]
        for state in chain:
            ...

    Constraints and updaters can also be added one at a time, in any order relative to the other
    configuration, with :meth:`add_constraint` and :meth:`add_updater`.

    ``acceptance_fn`` defaults to :func:`~gerrychain.accept.always_accept` and ``constraints``
    defaults to no constraints; ``proposal_fn``, ``initial_partition``, and ``total_steps`` must be
    set before iterating. While a run is in progress the configuration is locked: assigning any of
    these attributes (or ``rng``) raises AttributeError. The lock is released when the run ends,
    whether by exhausting the steps, an error in a step, or leaving the loop early with
    ``break``.
    """

    # "constraints" has no slot: it is a property whose storage is the "_validator" slot, and a
    # slot would collide with the property (both are class attributes of the same name).
    # Private names in __slots__ are mangled like any other class-body identifier.
    __slots__ = (
        "proposal_fn",
        "acceptance_fn",
        "initial_partition",
        "total_steps",
        "rng",
        "_validator",
        "_added_updaters",
        "state",
        "counter",
        "__locked",
    )

    @deprecated_parameters(
        renamed={
            "proposal": "proposal_fn",
            "accept": "acceptance_fn",
            "initial_state": "initial_partition",
        }
    )
    def __init__(
        self,
        proposal_fn: ProposalFn | None = None,
        constraints: Iterable[ConstraintFn] | ConstraintFn = (),
        acceptance_fn: AcceptanceFn = always_accept,
        initial_partition: Partition | None = None,
        total_steps: int | None = None,
        *,
        rng: random.Random | int | None = None,
    ) -> None:
        """Initialize a MarkovChain instance.

        All configuration parameters are optional here; whatever is omitted can be assigned
        later as an attribute. The full configuration is checked by :meth:`check_valid` when
        iteration begins.

        Args:
            proposal_fn (ProposalFn | None, optional): Function called as
                ``proposal_fn(state, rng=chain.rng)`` to propose the next state. The chain's RNG
                takes precedence over an ``rng`` bound into a ``functools.partial`` proposal.
            constraints (Iterable[ConstraintFn] | ConstraintFn, optional):
                One or more functions with signature ``Partition -> bool`` determining whether a
                proposed next state is valid. Bundled into a single :class:`Validator`; passing a
                Validator directly also works. Defaults to no constraints.
            acceptance_fn (AcceptanceFn, optional): Function called as
                ``acceptance_fn(proposed_state, rng=chain.rng)`` to accept or reject the proposed
                state. Defaults to :func:`~gerrychain.accept.always_accept`.
            initial_partition (Partition | None, optional): Initial Partition class.
            total_steps (int | None, optional): Number of steps to run.
            rng (random.Random | int | None, optional): Source of randomness for the run. An integer
                creates a reproducible ``random.Random``; a supplied instance is kept by identity;
                ``None`` creates an independent RNG from system entropy.

        Raises:
            ValueError: If an initial_partition is given and is not valid according to the
                given constraints.
        """
        self.__locked = False
        # Updaters registered before initial_partition is set; __setattr__ applies them when it is.
        self._added_updaters: dict[str, Callable[[Partition], Any]] = {}
        self.proposal_fn = proposal_fn
        self.acceptance_fn = acceptance_fn
        self.total_steps = total_steps
        self.initial_partition = initial_partition
        self.state = initial_partition
        self.rng = make_rng(rng)
        # Last: the setter validates initial_partition against the constraints when both are given.
        self.constraints = constraints

    @property
    def constraints(self) -> Validator:
        """The chain's constraints, bundled into a single :class:`Validator` callable.

        Returns:
            Validator: The constraints of the Markov chain.
        """
        return self._validator

    @constraints.setter
    def constraints(
        self,
        constraints: Iterable[ConstraintFn] | Validator | ConstraintFn,
    ) -> None:
        """Setter for the constraints property.

        If an initial partition has been set, checks that it is valid according to the new
        constraints being imposed on the Markov chain, and raises a ValueError listing the failed
        constraints if not. With no initial partition yet, the check is deferred to
        :meth:`check_valid`.

        Args:
            constraints (Iterable[ConstraintFn] | Validator | ConstraintFn): The new constraints
                to impose on the Markov chain.

        Raises:
            ValueError: If the initial_partition is set and not valid according to the new
                constraints.
        """

        if isinstance(constraints, Validator):
            validator = constraints
        elif callable(constraints):
            validator = Validator([cast(ConstraintFn, constraints)])
        else:
            validator = Validator(constraints)

        if self.initial_partition is not None:
            self._assert_initial_partition_valid(validator)

        self._validator = validator

    def add_constraint(self, constraint: ConstraintFn) -> None:
        """Add a constraint to the chain's existing constraints.

        If an initial partition is set, it is checked against the new constraint immediately;
        otherwise the check is deferred to :meth:`check_valid`.

        Args:
            constraint (ConstraintFn): A new constraint to add to the Markov chain.

        Raises:
            AttributeError: If a run is in progress.
            ValueError: If the initial partition fails the new constraint.
        """
        if self.__locked:
            raise AttributeError("Cannot add constraint to a locked MarkovChain instance.")

        validator = Validator([*self._validator.constraints, constraint])
        if self.initial_partition is not None:
            self._assert_initial_partition_valid(validator)
        self._validator = validator

    def add_constraints(self, constraints: Iterable[ConstraintFn]) -> None:
        """Add multiple constraints to the chain's existing constraints.

        If an initial partition is set, it is checked against the new constraints immediately;
        otherwise the check is deferred to :meth:`check_valid`.

        Args:
            constraints (Iterable[ConstraintFn]): New constraints to add to the Markov chain.

        Raises:
            AttributeError: If a run is in progress.
            ValueError: If the initial partition fails any of the new constraints.
        """
        if self.__locked:
            raise AttributeError("Cannot add constraints to a locked MarkovChain instance.")

        validator = Validator([*self._validator.constraints, *constraints])
        if self.initial_partition is not None:
            self._assert_initial_partition_valid(validator)
        self._validator = validator

    def add_updater(self, name: str, updater: Callable[[Partition], Any]) -> None:
        """Add a named updater to the chain's partitions.

        The updater is added to the initial partition (immediately if one is set, otherwise as
        soon as one is assigned) and is inherited by every partition the chain generates. Its
        value is accessed as ``partition[name]``.

        Args:
            name (str): Name under which the updater's value is accessed.
            updater (Callable[[Partition], Any]): The updater function.

        Raises:
            AttributeError: If a run is in progress.
        """
        if self.__locked:
            raise AttributeError("Cannot add updater to a locked MarkovChain instance.")

        self._added_updaters[name] = updater
        if self.initial_partition is not None:
            self.initial_partition.updaters[name] = updater

    def add_updaters(self, updaters: dict[str, Callable[[Partition], Any]]) -> None:
        """Add multiple named updaters to the chain's partitions.

        The updaters are added to the initial partition (immediately if one is set, otherwise as
        soon as one is assigned) and are inherited by every partition the chain generates. Their
        values are accessed as ``partition[name]``.

        Args:
            updaters (dict[str, Callable[[Partition], Any]]): A dictionary of updater functions,
                where keys are the names under which the updater's values are accessed.
        """
        if self.__locked:
            raise AttributeError("Cannot add updaters to a locked MarkovChain instance.")

        self._added_updaters.update(updaters)
        if self.initial_partition is not None:
            self.initial_partition.updaters.update(updaters)

    def _assert_initial_partition_valid(self, validator: Validator) -> None:
        """Raise ValueError naming the failed constraints if initial_partition fails them."""
        assert self.initial_partition is not None
        if validator(self.initial_partition):
            return
        failed = [
            constraint
            for constraint in validator.constraints
            if not constraint(self.initial_partition)
        ]
        raise ValueError(
            "The given initial_partition is not valid according to the constraints. "
            "The failed constraints were: "
            + ",".join(getattr(f, "__name__", type(f).__name__) for f in failed)
        )

    def check_valid(self) -> None:
        """Check that the chain is fully and consistently configured.

        This is called automatically when iteration begins, but can be called directly to
        fail fast after incremental configuration.

        Raises:
            ValueError: If ``proposal_fn``, ``initial_partition``, or ``total_steps`` is unset, or
                if the initial partition does not satisfy the constraints.
        """
        missing = [
            name
            for name in ("proposal_fn", "initial_partition", "total_steps")
            if getattr(self, name) is None
        ]
        if len(missing) > 0:
            raise ValueError("MarkovChain is not fully configured. Missing: " + ", ".join(missing))
        self._assert_initial_partition_valid(self._validator)

    def __lock(self) -> None:
        """Lock the Markov chain to prevent configuration changes while a run is in progress.

        Sets the private ``__locked`` flag; while it is set, assigning any configuration attribute
        raises an AttributeError. Run state (``counter``, ``state``) stays mutable.
        """
        self.__locked = True

    def __unlock(self) -> None:
        """Unlock the Markov chain to allow configuration changes again."""
        self.__locked = False

    def __setattr__(self, name: str, value: object) -> None:
        """Set an attribute on the Markov chain, with locking behavior.

        This method overrides the default attribute setting behavior to enforce a locking mechanism.
        If the Markov chain is locked (``__locked`` is ``True``), any attempt to set a configuration
        attribute will raise an AttributeError. Other attributes are always settable.

        Args:
            name (str): The name of the attribute to set.
            value (object): The value to assign to the attribute.

        Raises:
            AttributeError: If the Markov chain is locked and an attempt is made to set an
                attribute. Unknown attribute names are rejected by ``object.__setattr__``
                itself, since ``__slots__`` leaves instances without a ``__dict__``.
        """

        # The getattr default covers the first assignment in __init__, before the flag exists.
        if getattr(self, "_MarkovChain__locked", False) and name in (
            "proposal_fn",
            "constraints",
            "acceptance_fn",
            "initial_partition",
            "total_steps",
            "rng",
        ):
            raise AttributeError(f"Cannot set attribute '{name}' on a locked MarkovChain instance.")

        if name == "rng":
            if not isinstance(value, (random.Random, int, numpy.integer)) and value is not None:
                raise TypeError(
                    f"rng must be a random.Random instance, an int, or None; got {type(value)}"
                )
            value = make_rng(value)

        super().__setattr__(name, value)

        # Updaters added before an initial partition existed are applied once one is assigned.
        if name == "initial_partition" and value is not None:
            added = getattr(self, "_added_updaters", None)
            if added:
                cast(Partition, value).updaters.update(added)

    def __iter__(self) -> Iterator[Partition]:
        """Starts a fresh run of the Markov chain.

        Checks the configuration (see :meth:`check_valid`) and returns a generator over the run's
        states, starting from the initial state. The chain's RNG stream continues across runs.

        Returns:
            Iterator[Partition]: The states of the run, beginning with the initial state.

        Raises:
            ValueError: If the chain is not fully configured; see :meth:`check_valid`.
        """
        self.check_valid()

        proposal_fn = self.proposal_fn
        acceptance_fn = self.acceptance_fn
        total_steps = self.total_steps
        initial_partition = self.initial_partition
        assert proposal_fn is not None and total_steps is not None and initial_partition is not None

        proposal_fn = cast(
            ProposalFn,
            adapt_legacy_callable(proposal_fn, "Proposal function"),
        )
        acceptance_fn = cast(
            AcceptanceFn,
            adapt_legacy_callable(acceptance_fn, "Acceptance function"),
        )

        return self.__run(proposal_fn, acceptance_fn, total_steps, initial_partition)

    def __run(
        self,
        proposal_fn: ProposalFn,
        acceptance_fn: AcceptanceFn,
        total_steps: int,
        initial_partition: Partition,
    ) -> Iterator[Partition]:
        """Generator over one run: propose, validate, accept/reject, yield, for each step.

        Locked for exactly the lifetime of the run: a generator's ``finally`` runs once at the true
        end of iteration, whether that is exhaustion, an exception in a step, or the loop being
        exited early (Python closes the generator when the loop's iterator is discarded).
        """
        self.__lock()
        try:
            state = initial_partition
            self.state = state
            self.counter = 1
            yield state

            while self.counter < total_steps:
                proposed_next_state = proposal_fn(state, rng=self.rng)
                # Erase the parent of the parent, to avoid memory leak
                state.parent = None

                if self._validator(proposed_next_state):
                    if acceptance_fn(proposed_next_state, rng=self.rng):
                        state = proposed_next_state
                    self.state = state
                    self.counter += 1
                    yield state
        finally:
            self.__unlock()

    def __len__(self) -> int:
        """Returns the total number of steps in the Markov chain.

        Returns:
            int: The total number of steps in the Markov chain.

        Raises:
            ValueError: If total_steps has not been set.
        """
        if self.total_steps is None:
            raise ValueError("total_steps has not been set on this MarkovChain")
        return self.total_steps

    def __repr__(self) -> str:
        return f"<MarkovChain [{self.total_steps} steps]>"

    def with_progress_bar(self) -> Iterable[Partition]:
        """Wraps the Markov chain in a tqdm progress bar.

        Useful for long-running Markov chains where you want to keep track of the progress.
        Requires the `tqdm` package to be installed.

        Returns:
            Iterable[Partition]: A progress-reporting iterable over the chain.
        """
        from tqdm.auto import tqdm

        return tqdm(self)
