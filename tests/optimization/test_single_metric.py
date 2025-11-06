from gerrychain import Partition
from gerrychain.optimization import SingleMetricOptimizer
from gerrychain.constraints import contiguous
from gerrychain.proposals import recom
from gerrychain.updaters import Tally
from functools import partial
import numpy as np
import random

random.seed(2024)


def simple_cut_edge_count(partition):
    return len(partition["cut_edges"])


# ================
#   SHORT BURSTS
# ================


def test_single_metric_sb_attains_min_quickly(four_by_five_grid_for_opt):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "my_cut_edges": simple_cut_edge_count,
        },
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=simple_cut_edge_count,
        maximize=False,
    )

    total_steps = 200
    burst_length = 5

    min_scores_sb = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.short_bursts(
            burst_length=burst_length,
            num_bursts=total_steps // burst_length,
            with_progress_bar=True,
        )
    ):
        min_scores_sb[i] = optimizer.best_score

    assert np.min(min_scores_sb) == 11


def test_single_metric_tilted_sb_attains_min_quickly(four_by_five_grid_for_opt):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "my_cut_edges": simple_cut_edge_count,
        },
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=simple_cut_edge_count,
        maximize=False,
    )

    total_steps = 200
    burst_length = 5

    min_scores_sb = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.tilted_short_bursts(
            burst_length=burst_length,
            num_bursts=total_steps // burst_length,
            p=0.2,
            with_progress_bar=True,
        )
    ):
        min_scores_sb[i] = optimizer.best_score

    assert np.min(min_scores_sb) == 11


def test_single_metric_variable_len_sb_attains_min_quickly(four_by_five_grid_for_opt):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "my_cut_edges": simple_cut_edge_count,
        },
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=simple_cut_edge_count,
        maximize=False,
    )

    total_steps = 200

    min_scores_sb = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.variable_length_short_bursts(
            num_steps=total_steps,
            stuck_buffer=2,
            with_progress_bar=True,
        )
    ):
        min_scores_sb[i] = optimizer.best_score

    assert np.min(min_scores_sb) == 11


# ========================
#   SIMULATED ANNEALING
# ========================


def test_single_metric_sa_jumpcycle_attains_min_quickly(four_by_five_grid_for_opt):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "my_cut_edges": simple_cut_edge_count,
        },
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=simple_cut_edge_count,
        maximize=False,
    )

    total_steps = 200

    min_scores_anneal = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.simulated_annealing(
            total_steps,
            optimizer.jumpcycle_beta_function(10, 10),
            beta_magnitude=1,
            with_progress_bar=True,
        )
    ):
        min_scores_anneal[i] = optimizer.best_score

    assert np.min(min_scores_anneal) == 11


def test_single_metric_sa_lincycle_attains_min_quickly(four_by_five_grid_for_opt):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "my_cut_edges": simple_cut_edge_count,
        },
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=simple_cut_edge_count,
        maximize=False,
    )

    total_steps = 200

    min_scores_anneal = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.simulated_annealing(
            total_steps,
            optimizer.linearcycle_beta_function(10, 10, 10),
            beta_magnitude=1,
        )
    ):
        min_scores_anneal[i] = optimizer.best_score

    assert np.min(min_scores_anneal) == 11


def test_single_metric_sa_linear_jumpcycle_attains_min_quickly(
    four_by_five_grid_for_opt,
):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "my_cut_edges": simple_cut_edge_count,
        },
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=simple_cut_edge_count,
        maximize=False,
    )

    total_steps = 200

    min_scores_anneal = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.simulated_annealing(
            total_steps,
            optimizer.linear_jumpcycle_beta_function(10, 10, 10),
            beta_magnitude=1,
        )
    ):
        min_scores_anneal[i] = optimizer.best_score

    assert np.min(min_scores_anneal) == 11


def test_single_metric_sa_logitcycle_attains_min_quickly(four_by_five_grid_for_opt):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "my_cut_edges": simple_cut_edge_count,
        },
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=simple_cut_edge_count,
        maximize=False,
    )

    total_steps = 200

    min_scores_anneal = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.simulated_annealing(
            total_steps,
            optimizer.logitcycle_beta_function(10, 10, 10),
            beta_magnitude=1,
        )
    ):
        min_scores_anneal[i] = optimizer.best_score

    assert np.min(min_scores_anneal) == 11


def test_single_metric_sa_logit_jumpcycle_attains_min_quickly(
    four_by_five_grid_for_opt,
):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "my_cut_edges": simple_cut_edge_count,
        },
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=simple_cut_edge_count,
        maximize=False,
    )

    total_steps = 200

    min_scores_anneal = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.simulated_annealing(
            total_steps,
            optimizer.logit_jumpcycle_beta_function(10, 10, 10),
            beta_magnitude=1,
        )
    ):
        min_scores_anneal[i] = optimizer.best_score

    assert np.min(min_scores_anneal) == 11


# ===============
#   TILTED RUNS
# ===============


def test_single_metric_tilted_runs_attains_min_quickly_with_p_eq_0p1(
    four_by_five_grid_for_opt,
):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "my_cut_edges": simple_cut_edge_count,
        },
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=simple_cut_edge_count,
        maximize=False,
    )

    total_steps = 1000

    min_scores_tilt = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.tilted_run(num_steps=total_steps, p=0.1, with_progress_bar=True)
    ):
        min_scores_tilt[i] = optimizer.best_score

    assert np.min(min_scores_tilt) == 11


# ==========================
#   SOME HARDER TEST CASES
# ==========================


def test_single_metric_sb_finds_hard_max(four_by_five_grid_for_opt):
    random.seed(2024)

    def opt_fn(partition):
        mx = 10
        count = sum(1 for x in partition["opt_value_sum"].values() if x == mx)
        return count

    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={"opt_value_sum": Tally("opt_value", alias="opt_value_sum")},
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=opt_fn,
        maximize=True,
    )

    total_steps = 10000
    burst_length = 100

    max_scores_sb = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.short_bursts(
            burst_length=burst_length,
            num_bursts=total_steps // burst_length,
            with_progress_bar=True,
        )
    ):
        max_scores_sb[i] = optimizer.best_score

    assert np.max(max_scores_sb) == 2


def test_single_metric_sa_finds_hard_max(four_by_five_grid_for_opt):
    random.seed(2024)

    def opt_fn(partition):
        mx = 10
        count = sum(1 for x in partition["opt_value_sum"].values() if x == mx)
        return count

    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={"opt_value_sum": Tally("opt_value", alias="opt_value_sum")},
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=opt_fn,
        maximize=True,
    )

    total_steps = 20000

    max_scores_anneal = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.simulated_annealing(
            total_steps,
            optimizer.linear_jumpcycle_beta_function(100, 100, 100),
            beta_magnitude=1,
        )
    ):
        max_scores_anneal[i] = optimizer.best_score

    assert np.max(max_scores_anneal) == 2


def test_single_metric_tilted_runs_finds_hard_max(four_by_five_grid_for_opt):
    random.seed(2024)

    def opt_fn(partition):
        mx = 10
        count = sum(1 for x in partition["opt_value_sum"].values() if x == mx)
        return count

    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={"opt_value_sum": Tally("opt_value", alias="opt_value_sum")},
    )

    ideal_pop = sum(initial_partition["population"].values()) / 4

    proposal = partial(
        recom,
        pop_col="population",
        pop_target=ideal_pop,
        epsilon=0.0,
        node_repeats=1,
    )

    optimizer = SingleMetricOptimizer(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        optimization_metric=opt_fn,
        maximize=True,
    )

    total_steps = 10000

    max_scores_tilt = np.zeros(total_steps)
    for i, part in enumerate(
        optimizer.tilted_run(num_steps=total_steps, p=0.1, with_progress_bar=True)
    ):
        max_scores_tilt[i] = optimizer.best_score

    assert np.max(max_scores_tilt) == 2
