import functools

import matplotlib.pyplot as plt

from rundmcmc.defaults import BasicChain, PA_partition
from rundmcmc.run import pipe_to_table
from rundmcmc.scores import efficiency_gap, mean_median, mean_thirdian
from rundmcmc.validity import L1_reciprocal_polsby_popper


def main():
    initial_partition = PA_partition()

    chain = BasicChain(initial_partition, total_steps=10000)

    scores = {
        'Mean-Median': functools.partial(mean_median, proportion_column_name='VoteA%'),
        'Mean-Thirdian': functools.partial(mean_thirdian, proportion_column_name='VoteA%'),
        'Efficiency Gap': functools.partial(efficiency_gap, col1='VoteA', col2='VoteB'),
        'L1 Reciprocal Polsby-Popper': L1_reciprocal_polsby_popper
    }

    initial_scores = {key: score(initial_partition) for key, score in scores.items()}

    table = pipe_to_table(chain, scores)

    fig, axes = plt.subplots(2, 2)

    quadrants = {
        'Mean-Median': (0, 0),
        'Mean-Thirdian': (0, 1),
        'Efficiency Gap': (1, 0),
        'L1 Reciprocal Polsby-Popper': (1, 1)
    }

    for key in scores:
        quadrant = quadrants[key]
        axes[quadrant].hist(table[key], bins=50)
        axes[quadrant].set_title(key)
        axes[quadrant].axvline(x=initial_scores[key], color='r')
    plt.show()


if __name__ == '__main__':
    main()
