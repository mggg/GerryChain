from rundmcmc.scores import efficiency_gap, mean_median, mean_thirdian
from rundmcmc.validity import L1_reciprocal_polsby_popper
from rundmcmc.defaults import BasicChain, PA_partition
from multiprocessing import Pool
from collections import Counter
import functools

initial_partition = PA_partition()

double_walk_length = 10_000
first_walk_length = 1_000

n_star_chains = 4
star_chain_length = 10_000

scores = {
    'Mean-Median': functools.partial(mean_median, proportion_column_name='VoteA%'),
    'Mean-Thirdian': functools.partial(mean_thirdian, proportion_column_name='VoteA%'),
    'Efficiency Gap': functools.partial(efficiency_gap, col1='VoteA', col2='VoteB'),
    'L1 Reciprocal Polsby-Popper': L1_reciprocal_polsby_popper
}


def run_chain(partition, length):
    chain = BasicChain(initial_partition, total_steps=length)
    score_dict = {name: [] for name in scores.keys()}

    for partition in chain:
        for name, func in scores.items():
            score_dict[name].append(func(partition))

    return partition, score_dict


def p_report_star(score_name, n_branches, ensemble_scores, initial_plan_score):
    """Report the p-value from a star of chains."""
    count_higher = Counter(score >= initial_plan_score for score in ensemble_scores)
    total_scores = sum(count_higher.values())
    fraction_as_high = count_higher[True] / total_scores
    fraction_lower = count_higher[False] / total_scores

    p_value = fraction_as_high / n_branches
    opposite_p_value = fraction_lower / n_branches

    report = {'name': score_name,
              'initial_plan_score': initial_plan_score,
              'fraction_as_high': fraction_as_high,
              'p_value': p_value,
              'opposite_p_value': opposite_p_value}

    return report


first_end, first_ensemble = run_chain(initial_partition, first_walk_length)
second_end, second_ensemble = run_chain(first_end, double_walk_length - first_walk_length)

with Pool() as p:
    func = functools.partial(run_chain, length=star_chain_length)
    star_partitions = p.map(func, [second_end] * n_star_chains)

ensembles = dict()

for name in scores.keys():
    data = first_ensemble[name]
    data += second_ensemble[name]

    for _, ensemble in star_partitions:
        data += ensemble[name]

    ensembles[name] = data

    print(p_report_star(name, n_star_chains, data, first_ensemble[name][0]))
