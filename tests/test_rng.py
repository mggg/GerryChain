"""Tests for explicitly owned GerryChain RNGs."""

import random
from functools import partial

import numpy as np
import pytest

from gerrychain import MarkovChain, Partition
from gerrychain._rng import make_rng
from gerrychain.accept import always_accept
from gerrychain.constraints import contiguous
from gerrychain.optimization import SingleMetricOptimizer
from gerrychain.proposals import recom
from gerrychain.updaters import Tally, cut_edges

# String part labels on purpose: they exercise the sorted() set-to-sequence conversions
# that make chains independent of PYTHONHASHSEED.
PART_LABELS = ["a", "b", "c", "d"]


def initial_partition(graph):
    # Each row of the 4x5 grid is one district: connected, population 50 each.
    assignment = {node: PART_LABELS[node // 5] for node in range(20)}
    return Partition(
        graph,
        assignment,
        {"population": Tally("population", alias="population"), "cut_edges": cut_edges},
    )


def make_recom_chain(graph, rng=None, total_steps=25):
    proposal = partial(recom, pop_col="population", pop_target=50, epsilon=0.0)
    return MarkovChain(
        proposal, [contiguous], always_accept, initial_partition(graph), total_steps, rng=rng
    )


def trajectory(chain):
    return [dict(part.assignment.mapping) for part in chain]


def make_optimizer(graph, rng=None):
    proposal = partial(recom, pop_col="population", pop_target=50, epsilon=0.0)
    return SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition(graph),
        optimization_metric=lambda part: len(part["cut_edges"]),
        maximize=False,
        rng=rng,
    )


def run_bursts(optimizer):
    return [
        dict(part.assignment.mapping)
        for part in optimizer.short_bursts(burst_length=5, num_bursts=4)
    ]


def test_same_int_seed_reproduces(four_by_five_grid_for_opt):
    first = trajectory(make_recom_chain(four_by_five_grid_for_opt, rng=5))
    second = trajectory(make_recom_chain(four_by_five_grid_for_opt, rng=5))
    assert first == second


def test_different_seeds_differ(four_by_five_grid_for_opt):
    first = trajectory(make_recom_chain(four_by_five_grid_for_opt, rng=5))
    second = trajectory(make_recom_chain(four_by_five_grid_for_opt, rng=6))
    assert first != second


def test_random_instance_is_passed_to_proposal(four_by_five_grid_for_opt):
    instance = random.Random(3)
    seen = []

    def proposal(partition, *, rng):
        seen.append(rng)
        return partition

    chain = MarkovChain(
        proposal,
        [contiguous],
        always_accept,
        initial_partition(four_by_five_grid_for_opt),
        2,
        rng=instance,
    )
    trajectory(chain)

    assert seen == [instance]


def test_proposal_error_propagates(four_by_five_grid_for_opt):
    instance = random.Random(3)

    def proposal(_partition, *, rng):
        assert rng is instance
        raise RuntimeError("proposal failed")

    chain = iter(
        MarkovChain(
            proposal,
            [contiguous],
            always_accept,
            initial_partition(four_by_five_grid_for_opt),
            2,
            rng=instance,
        )
    )
    next(chain)
    with pytest.raises(RuntimeError, match="proposal failed"):
        next(chain)


def test_make_rng_rejects_unsupported_types():
    with pytest.raises(TypeError):
        make_rng("2018")

    with pytest.raises(TypeError):
        make_rng(True)


def test_make_rng_accepts_numpy_integer_seed():
    numpy_seeded = make_rng(np.int64(5))
    assert numpy_seeded.random() == random.Random(5).random()


def test_chain_without_rng_owns_an_independent_instance(four_by_five_grid_for_opt):
    first = make_recom_chain(four_by_five_grid_for_opt)
    second = make_recom_chain(four_by_five_grid_for_opt)
    assert first.rng is not second.rng


def test_later_construction_does_not_reseed_earlier_chain(four_by_five_grid_for_opt):
    baseline = trajectory(make_recom_chain(four_by_five_grid_for_opt, rng=1))
    chain_a = make_recom_chain(four_by_five_grid_for_opt, rng=1)
    make_recom_chain(four_by_five_grid_for_opt, rng=2)  # constructed, never run
    assert trajectory(chain_a) == baseline


def test_interleaved_chains_keep_separate_streams(four_by_five_grid_for_opt):
    baseline_a = trajectory(make_recom_chain(four_by_five_grid_for_opt, rng=1, total_steps=15))
    baseline_b = trajectory(make_recom_chain(four_by_five_grid_for_opt, rng=2, total_steps=15))
    chain_a = iter(make_recom_chain(four_by_five_grid_for_opt, rng=1, total_steps=15))
    chain_b = iter(make_recom_chain(four_by_five_grid_for_opt, rng=2, total_steps=15))

    actual_a = []
    actual_b = []
    for _ in range(15):
        actual_a.append(dict(next(chain_a).assignment.mapping))
        actual_b.append(dict(next(chain_b).assignment.mapping))

    assert actual_a == baseline_a
    assert actual_b == baseline_b


def test_reiterating_with_int_seed_continues_stream(four_by_five_grid_for_opt):
    chain = make_recom_chain(four_by_five_grid_for_opt, rng=5)
    assert trajectory(chain) != trajectory(chain)


def test_reiterating_with_random_instance_continues_stream(four_by_five_grid_for_opt):
    chain = make_recom_chain(four_by_five_grid_for_opt, rng=random.Random(5))
    assert trajectory(chain) != trajectory(chain)


def test_optimizer_rerun_continues_stream(four_by_five_grid_for_opt):
    optimizer = make_optimizer(four_by_five_grid_for_opt, rng=11)
    first = run_bursts(optimizer)
    # Consecutive bursts continue one stream, so re-running the same optimizer does
    # not repeat its trajectory; construct a fresh optimizer to reproduce a run.
    assert run_bursts(optimizer) != first
    assert run_bursts(make_optimizer(four_by_five_grid_for_opt, rng=11)) == first
