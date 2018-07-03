import functools

from rundmcmc.defaults import BasicChain, PA_partition
from rundmcmc.output import p_value_report
from rundmcmc.run import pipe_to_table
from rundmcmc.scores import efficiency_gap, mean_median, mean_thirdian


def main():
    initial_partition = PA_partition()

    chain = BasicChain(initial_partition, total_steps=10000)

    scores = {
        'Mean-Median': functools.partial(mean_median, proportion_column_name='VoteA%'),
        'Mean-Thirdian': functools.partial(mean_thirdian, proportion_column_name='VoteA%'),
        'Efficiency Gap': functools.partial(efficiency_gap, col1='VoteA', col2='VoteB'),
    }

    initial_scores = {key: score(initial_partition) for key, score in scores.items()}

    table = pipe_to_table(chain, scores)

    return {key: p_value_report(key, table[key], initial_scores[key]) for key in scores}


if __name__ == '__main__':
    main()
