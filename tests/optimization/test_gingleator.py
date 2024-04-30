from gerrychain import Partition
from gerrychain.optimization import Gingleator
from gerrychain.constraints import contiguous
from gerrychain.proposals import recom
from gerrychain.updaters import Tally
from functools import partial
import pytest
import numpy as np
import random

random.seed(2024)


def simple_cut_edge_count(partition):
    return len(partition["cut_edges"])


def gingleator_test_partition(four_by_five_grid_for_opt):
    return Partition(
        graph=four_by_five_grid_for_opt,
        assignment={
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 1,
            6: 1,
            7: 1,
            8: 1,
            9: 1,
            10: 2,
            11: 2,
            12: 2,
            13: 2,
            14: 2,
            15: 3,
            16: 3,
            17: 3,
            18: 3,
            19: 3,
        },
        updaters={
            "population": Tally("population", alias="population"),
            "MVAP": Tally("MVAP", alias="MVAP"),
            "m_perc": lambda p_dict: {
                key: p_dict["MVAP"][key] / p_dict["population"][key]
                for key in p_dict["MVAP"]
            },
            "my_cut_edges": simple_cut_edge_count,
        },
    )


def test_ginglator_needs_min_perc_or_min_pop_col(four_by_five_grid_for_opt):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "MVAP": Tally("MVAP", alias="MVAP"),
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

    with pytest.raises(ValueError) as gingle_err:
        gingles = Gingleator(
            proposal=proposal,
            constraints=[contiguous],
            initial_state=initial_partition,
            total_pop_col="population",
            score_function=Gingleator.num_opportunity_dists,
        )

    assert "`minority_perc_col` and `minority_pop_col` cannot both be `None`" in str(
        gingle_err.value
    )


def test_ginglator_warns_if_min_perc_and_min_pop_col_set(four_by_five_grid_for_opt):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "MVAP": Tally("MVAP", alias="MVAP"),
            "m_perc": lambda p_dict: {
                key: p_dict["MVAP"][key] / p_dict["population"][key]
                for key in p_dict["MVAP"]
            },
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

    with pytest.warns() as record:
        gingles = Gingleator(
            proposal=proposal,
            constraints=[contiguous],
            initial_state=initial_partition,
            total_pop_col="population",
            minority_pop_col="MVAP",
            minority_perc_col="m_perc",
            score_function=Gingleator.num_opportunity_dists,
        )

    assert "`minority_perc_col` and `minority_pop_col` are both specified" in str(
        record.list[0].message
    )


def test_gingleator_finds_best_partition(four_by_five_grid_for_opt):
    random.seed(2024)
    initial_partition = Partition.from_random_assignment(
        graph=four_by_five_grid_for_opt,
        n_parts=4,
        epsilon=0.0,
        pop_col="population",
        updaters={
            "population": Tally("population", alias="population"),
            "MVAP": Tally("MVAP", alias="MVAP"),
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

    gingles = Gingleator(
        proposal=proposal,
        constraints=[contiguous],
        initial_state=initial_partition,
        minority_pop_col="MVAP",
        total_pop_col="population",
        score_function=Gingleator.num_opportunity_dists,
    )

    total_steps = 5000
    burst_length = 10

    max_scores_sb = np.zeros(total_steps)
    for i, part in enumerate(
        gingles.short_bursts(
            burst_length=burst_length,
            num_bursts=total_steps // burst_length,
            with_progress_bar=True,
        )
    ):
        max_scores_sb[i] = gingles.best_score

    assert max(max_scores_sb) == 2


def test_count_num_opportunity_dists(four_by_five_grid_for_opt):
    initial_partition = gingleator_test_partition(four_by_five_grid_for_opt)

    assert Gingleator.num_opportunity_dists(initial_partition, "m_perc", 0.5) == 2
    assert Gingleator.num_opportunity_dists(initial_partition, "m_perc", 0.6) == 0


def test_reward_partial_dist(four_by_five_grid_for_opt):
    initial_partition = gingleator_test_partition(four_by_five_grid_for_opt)

    assert Gingleator.reward_partial_dist(initial_partition, "m_perc", 0.5) == 2 + 0.2
    assert Gingleator.reward_partial_dist(initial_partition, "m_perc", 0.6) == 0.52


def test_reward_next_highest_close(four_by_five_grid_for_opt):
    initial_partition = gingleator_test_partition(four_by_five_grid_for_opt)

    assert Gingleator.reward_next_highest_close(initial_partition, "m_perc", 0.5) == 2
    # Rounding needed here because of floating point arithmetic
    assert (
        round(
            Gingleator.reward_next_highest_close(initial_partition, "m_perc", 0.29), 5
        )
        == 2 + 0.1
    )


def test_penalize_maximum_over(four_by_five_grid_for_opt):
    initial_partition = gingleator_test_partition(four_by_five_grid_for_opt)

    assert (
        Gingleator.penalize_maximum_over(initial_partition, "m_perc", 0.5)
        == 2.0 + 0.48 / 0.50
    )

    assert Gingleator.penalize_maximum_over(initial_partition, "m_perc", 0.6) == 0


def test_penalize_avg_over(four_by_five_grid_for_opt):
    initial_partition = gingleator_test_partition(four_by_five_grid_for_opt)

    assert (
        Gingleator.penalize_avg_over(initial_partition, "m_perc", 0.5)
        == 2.0 + 0.48 / 0.50
    )

    assert Gingleator.penalize_avg_over(initial_partition, "m_perc", 0.6) == 0
