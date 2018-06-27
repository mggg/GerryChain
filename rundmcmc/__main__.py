from rundmcmc.defaults import BasicChain, example_partition
from rundmcmc.scores import mean_median, mean_thirdian
from rundmcmc.proposals import number_of_flips


def print_summary(partition, scores):
    print("")
    for name, score in scores.items():
        print(f"{name}: {score(partition, 'PR_DV08%')}")
    print(f"Polsby-Popper: {partition['polsby_popper']}")


def main():
    initial_partition = example_partition()

    chain = BasicChain(initial_partition, total_steps=10000)

    scores = {
        'Mean-Median': mean_median,
        'Mean-Thirdian': mean_thirdian
    }

    test_counties = ["007", "099", "205", "127"]

    prev_partition = {}
    dict_of_flips = {}

    for partition in chain:
        print_summary(partition, scores)
        dict_of_flips, prev_partition = number_of_flips(partition.flips, dict_of_flips, prev_partition)
        print(dict_of_flips)
        for county in test_counties:
            info = partition["counties"][county]
            print(f"county {county}: {info.split} ({info.contains})")

if __name__ == "__main__":
    main()
