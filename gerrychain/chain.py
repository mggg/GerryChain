"""
This module provides the MarkovChain class, which is designed to facilitate the creation
and iteration of Markov chains in the context of political redistricting and gerrymandering
analysis. It allows for the exploration of different districting plans based on specified
constraints and acceptance criteria.

Key Components:

- MarkovChain: The main class used for creating and iterating over Markov chain states.
- Validator: A helper class for validating proposed states in the Markov chain. See
  :class:`~gerrychain.constraints.Validator` for more details.


Usage:
The primary use of this module is to create an instance of MarkovChain with appropriate
parameters like proposal function, constraints, acceptance function, and initial state,
and then to iterate through the states of the Markov chain, yielding a new proposal
at each step.

Dependencies:

- typing: Used for type hints.

Last Updated: 11 Jan 2024
"""

from typing import Union, Iterable, Callable, Optional

from gerrychain.constraints import Validator, Bounds
from gerrychain.partition import Partition


class MarkovChain:
    """
    MarkovChain is a class that creates an iterator for iterating over the states
    of a Markov chain run in a gerrymandering analysis context.

    It allows for the generation of a sequence of partitions (states) of a political
    districting plan, where each partition represents a possible state in the Markov chain.

    Example usage:

    .. code-block:: python

        chain = MarkovChain(proposal, constraints, accept, initial_state, total_steps)
        for state in chain:
            # Do whatever you want - print output, compute scores, ...

    """

    def __init__(
        self,
        proposal: Callable,
        constraints: Union[Iterable[Callable], Validator, Iterable[Bounds], Callable],
        accept: Callable,
        initial_state: Partition,
        total_steps: int,
    ) -> None:
        """
        :param proposal: Function proposing the next state from the current state.
        :type proposal: Callable
        :param constraints: A function with signature ``Partition -> bool`` determining whether
            the proposed next state is valid (passes all binary constraints). Usually
            this is a :class:`~gerrychain.constraints.Validator` class instance.
        :type constraints: Union[Iterable[Callable], Validator, Iterable[Bounds], Callable]
        :param accept: Function accepting or rejecting the proposed state. In the most basic
            use case, this always returns ``True``. But if the user wanted to use a
            Metropolis-Hastings acceptance rule, this is where you would implement it.
        :type accept: Callable
        :param initial_state: Initial :class:`gerrychain.partition.Partition` class.
        :type initial_state: Partition
        :param total_steps: Number of steps to run.
        :type total_steps: int

        :returns: None

        :raises ValueError: If the initial_state is not valid according to the constraints.
        """
        if callable(constraints):
            is_valid = Validator([constraints])
        else:
            is_valid = Validator(constraints)

        if not is_valid(initial_state):
            failed = [
                constraint
                for constraint in is_valid.constraints  # type: ignore
                if not constraint(initial_state)
            ]
            message = (
                "The given initial_state is not valid according is_valid. "
                "The failed constraints were: " + ",".join([f.__name__ for f in failed])
            )
            raise ValueError(message)

        self.proposal = proposal
        self.is_valid = is_valid
        self.accept = accept
        self.total_steps = total_steps
        self.initial_state = initial_state
        self.state = initial_state

    @property
    def constraints(self) -> Validator:
        """
        Read_only alias for the is_valid property.
        Returns the constraints of the Markov chain.

        :returns: The constraints of the Markov chain.
        :rtype: String
        """
        return self.is_valid

    @constraints.setter
    def constraints(
        self,
        constraints: Union[Iterable[Callable], Validator, Iterable[Bounds], Callable],
    ) -> None:
        """
        Setter for the is_valid property.
        Checks if the initial state is valid according to the new constraints.
        being imposed on the Markov chain, and raises a ValueError if the
        initial state is not valid and lists the failed constraints.

        :param constraints: The new constraints to be imposed on the Markov chain.
        :type constraints: Union[Iterable[Callable], Validator, Iterable[Bounds], Callable]

        :returns: None

        :raises ValueError: If the initial_state is not valid according to the new constraints.
        """

        if callable(constraints):
            is_valid = Validator([constraints])
        else:
            is_valid = Validator(constraints)

        if not is_valid(self.initial_state):
            failed = [
                constraint
                for constraint in is_valid.constraints  # type: ignore
                if not constraint(self.initial_state)
            ]
            message = (
                "The given initial_state is not valid according to the new constraints. "
                "The failed constraints were: " + ",".join([f.__name__ for f in failed])
            )
            raise ValueError(message)

        self.is_valid = is_valid

    def __iter__(self) -> "MarkovChain":
        """
        Resets the Markov chain iterator.

        This method is called when an iterator is required for a container. It sets the
        counter to 0 and resets the state to the initial state.

        :returns: Returns itself as an iterator object.
        :rtype: MarkovChain
        """
        self.counter = 0
        self.state = self.initial_state
        return self

    def __next__(self) -> Optional[Partition]:
        """
        Advances the Markov chain to the next state.

        This method is called to get the next item in the iteration.
        It proposes the next state and moves to it if that state is
        valid according to the constraints and if accepted by the
        acceptance function. If the total number of steps has been
        reached, it raises a StopIteration exception.

        :returns: The next state of the Markov chain.
        :rtype: Optional[Partition]

        :raises StopIteration: If the total number of steps has been reached.
        """
        if self.counter == 0:
            self.counter += 1
            return self.state

        while self.counter < self.total_steps:
            proposed_next_state = self.proposal(self.state)
            # Erase the parent of the parent, to avoid memory leak
            if self.state is not None:
                self.state.parent = None

            if self.is_valid(proposed_next_state):
                if self.accept(proposed_next_state):
                    self.state = proposed_next_state
                self.counter += 1
                return self.state
        raise StopIteration

    def __len__(self) -> int:
        """
        Returns the total number of steps in the Markov chain.

        :returns: The total number of steps in the Markov chain.
        :rtype: int
        """
        return self.total_steps

    def __repr__(self) -> str:
        return "<MarkovChain [{} steps]>".format(len(self))

    def with_progress_bar(self):
        """
        Wraps the Markov chain in a tqdm progress bar.

        Useful for long-running Markov chains where you want to keep track
        of the progress. Requires the `tqdm` package to be installed.

        :returns: A tqdm-wrapped Markov chain.
        """
        from tqdm.auto import tqdm

        return tqdm(self)
