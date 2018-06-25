from rundmcmc.defaults import BasicChain, example_partition
from rundmcmc.scores import mean_median, mean_thirdian


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

    for partition in chain:
        print_summary(partition, scores)


if __name__ == "__main__":
    main()
